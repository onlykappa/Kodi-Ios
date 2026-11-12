// kr_upscale (r48, DEC-039/DEC-040): Apple's AI super resolution for prepared copies, iPhone build only.
// Pattern from Apple's WWDC25 sample "Enhancing your app with machine learning-based video effects"
// (SuperResolutionScaler.swift / LowLatencySuperResolutionScaler.swift): check isSupported, make the configuration,
// make sure its model is on the phone, startSession, then one processWithParameters per picture in presentation
// order (the video model also gets the previous source picture and the previous result), endSession.
// Limits (Apple's documentation, iOS 26): the video model takes at most 1440x1080 on iOS, the image model at most
// 1920x1080; factors come from supportedScaleFactors. kr_video fits the engine's result to the exact target.
#import <Foundation/Foundation.h>
#import <UIKit/UIKit.h>
#import <CoreMedia/CoreMedia.h>
#import <CoreVideo/CoreVideo.h>
#import <VideoToolbox/VideoToolbox.h>
#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "kr_upscale.h"
#include "kr_remux.h"

#if defined(__IPHONE_OS_VERSION_MAX_ALLOWED) && __IPHONE_OS_VERSION_MAX_ALLOWED >= 260000
#import <VideoToolbox/VTFrameProcessor.h>
#import <VideoToolbox/VTFrameProcessorFrame.h>
#import <VideoToolbox/VTFrameProcessor_SuperResolutionScaler.h>
#import <VideoToolbox/VTFrameProcessor_LowLatencySuperResolutionScaler.h>
#define KR_SR 1
#endif

// r49 (owner logs 0afdfd7b / 1ff17f50, ISSUE-180): on the owner's iPhone the AI models make 4x pictures only and the
// video model takes no 1080p, so 1080p -> 4K made 7680x4320 frames (about 265 MB each) and iOS closed Kodi. Now a model
// is used only when its result is no larger than asked (5 % slack), and the low-latency model, which takes at most
// 1280x1280, works on tiles: the picture is cut into overlapping tiles small enough for it, each is enlarged, and the
// tiles' middles are joined into one picture (64-bit half-float RGBA; a 4K picture is about 66 MB).
typedef struct { int cols, rows, tw, th; } kr_tiles;
#define KR_TILE_MARGIN 16         // source pixels each tile reaches past its own part, so the joins do not show
#define KR_SLACK 1.05

struct kr_upscale {
    int cols, rows, tw, th;       // tiles (cols 0: the whole picture at once)
    double f;                     // the engine's factor
    VTPixelTransferSessionRef crop;   // source -> one tile (its own session: it carries the crop rectangle)
    CVPixelBufferPoolRef tile_pool, big_pool;   // a tile's result in RGBA half float; the joined picture
    void *processor;              // VTFrameProcessor (retained, CFBridgingRetain)
    void *config;                 // its configuration
    int engine, w, h, ow, oh;     // ow x oh: what the engine makes (its factor times the source)
    VTPixelTransferSessionRef xfer;
    CVPixelBufferPoolRef in_pool, out_pool;
    CVPixelBufferRef prev_in, prev_out;
    double prev_t;
    double busy_ms;
    long frames;
    char name[96];
};

static double now_ms(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec * 1e3 + t.tv_nsec / 1e6; }
static void seterr(char *err, int n, NSString *text) { if (err && n > 0) snprintf(err, (size_t)n, "%s", text.UTF8String ?: "upscale error"); }
static const char *engine_word(int engine) {
    switch (engine) {
        case KR_UP_AI_VIDEO: return "ai-video";
        case KR_UP_AI_IMAGE: return "ai-image";
        case KR_UP_AI_FAST: return "ai-fast";
        case KR_UP_LANCZOS: return "lanczos";
        default: return "none";
    }
}

#ifdef KR_SR
// The smallest factor that reaches the target (2 % slack), else the largest there is.
static double pick_factor(NSArray<NSNumber *> *factors, double need) {
    double best = 0, largest = 0;
    for (NSNumber *n in factors) {
        double f = n.doubleValue;
        if (f > largest) largest = f;
        if (f >= need - 0.02 && (best == 0 || f < best)) best = f;
    }
    return best > 0 ? best : largest;
}
static double needed(int w, int h, int ow, int oh) { return fmax((double)ow / fmax(1, w), (double)oh / fmax(1, h)); }
// A factor whose picture would be larger than asked (the 4x model for a 2x need) is refused, not shrunk afterwards.
__attribute__((unused)) static int overshoots(double f, double need) { return need > 1.0 && f > need * KR_SLACK + 0.01; }
// The fewest tiles that fit the low-latency model's largest frame, each reaching KR_TILE_MARGIN past its part.
__attribute__((unused)) static int plan_tiles(int w, int h, int mxw, int mxh, kr_tiles *t) {
    t->cols = t->rows = 0;
    for (int c = 1; c <= 8 && !t->cols; c++) {
        int inner = (((w + c - 1) / c) + 1) & ~1;
        int tw = c == 1 ? w : inner + 2 * KR_TILE_MARGIN;
        if (tw > w) tw = w;
        if (tw <= mxw) { t->cols = c; t->tw = tw; }
    }
    for (int r = 1; r <= 8 && !t->rows; r++) {
        int inner = (((h + r - 1) / r) + 1) & ~1;
        int th = r == 1 ? h : inner + 2 * KR_TILE_MARGIN;
        if (th > h) th = h;
        if (th <= mxh) { t->rows = r; t->th = th; }
    }
    return t->cols && t->rows;
}

// The configuration for one engine, nil when it does not take this size on this phone.
static id make_config(int engine, int w, int h, int ow, int oh, double *factor, kr_tiles *tiles) API_AVAILABLE(ios(26.0)) {
    *factor = 0;
    if (tiles) tiles->cols = tiles->rows = 0;
    double need = needed(w, h, ow, oh);
    if (engine == KR_UP_AI_VIDEO || engine == KR_UP_AI_IMAGE) {
        if (!VTSuperResolutionScalerConfiguration.isSupported) return nil;
        double f = pick_factor(VTSuperResolutionScalerConfiguration.supportedScaleFactors, need);
        if (f < 1.5 || overshoots(f, need)) return nil;
        VTSuperResolutionScalerConfiguration *c = [[VTSuperResolutionScalerConfiguration alloc]
            initWithFrameWidth:w frameHeight:h scaleFactor:(NSInteger)llround(f)
                     inputType:engine == KR_UP_AI_VIDEO ? VTSuperResolutionScalerConfigurationInputTypeVideo
                                                        : VTSuperResolutionScalerConfigurationInputTypeImage
            usePrecomputedFlow:NO
         qualityPrioritization:VTSuperResolutionScalerConfigurationQualityPrioritizationNormal
                      revision:VTSuperResolutionScalerConfiguration.defaultRevision];
        if (c) *factor = (double)llround(f);
        return c;
    }
    if (engine == KR_UP_AI_FAST) {
        if (!VTLowLatencySuperResolutionScalerConfiguration.isSupported) return nil;
        CMVideoDimensions mx = VTLowLatencySuperResolutionScalerConfiguration.maximumDimensions;
        CMVideoDimensions mn = VTLowLatencySuperResolutionScalerConfiguration.minimumDimensions;
        if (w < mn.width || h < mn.height) return nil;
        kr_tiles t = { 1, 1, w, h };
        if ((w > mx.width || h > mx.height) && !plan_tiles(w, h, mx.width, mx.height, &t)) return nil;
        if (t.tw < mn.width || t.th < mn.height) return nil;
        double f = pick_factor([VTLowLatencySuperResolutionScalerConfiguration supportedScaleFactorsForFrameWidth:t.tw frameHeight:t.th], need);
        if (f < 1.2 || overshoots(f, need)) return nil;
        VTLowLatencySuperResolutionScalerConfiguration *c =
            [[VTLowLatencySuperResolutionScalerConfiguration alloc] initWithFrameWidth:t.tw frameHeight:t.th scaleFactor:(float)f];
        if (c) {
            *factor = f;
            if (tiles && (t.cols > 1 || t.rows > 1)) *tiles = t;
        }
        return c;
    }
    return nil;
}
// AUTO: the video model (uses neighbouring frames), then the image model, then the low-latency one.
static id choose(int want, int w, int h, int ow, int oh, int *engine, double *factor, kr_tiles *tiles) API_AVAILABLE(ios(26.0)) {
    int order[3] = { KR_UP_AI_VIDEO, KR_UP_AI_IMAGE, KR_UP_AI_FAST };
    for (int i = 0; i < 3; i++) {
        if (want != KR_UP_AUTO && want != order[i]) continue;
        id c = make_config(order[i], w, h, ow, oh, factor, tiles);
        if (c) { *engine = order[i]; return c; }
    }
    *engine = -1;
    return nil;
}
static int model_status(id c) API_AVAILABLE(ios(26.0)) {
    if (![c isKindOfClass:VTSuperResolutionScalerConfiguration.class]) return 2;   // low latency: loaded at startSession
    switch (((VTSuperResolutionScalerConfiguration *)c).configurationModelStatus) {
        case VTSuperResolutionScalerConfigurationModelStatusReady: return 2;
        case VTSuperResolutionScalerConfigurationModelStatusDownloading: return 1;
        default: return 0;
    }
}
static NSString *factors_json(NSArray<NSNumber *> *factors) {
    NSMutableArray *parts = [NSMutableArray array];
    for (NSNumber *n in factors) [parts addObject:[NSString stringWithFormat:@"%g", n.doubleValue]];
    return [NSString stringWithFormat:@"[%@]", [parts componentsJoinedByString:@","]];
}
static NSString *formats_json(NSArray<NSNumber *> *formats) {
    NSMutableArray *parts = [NSMutableArray array];
    for (NSNumber *n in formats) {
        uint32_t f = n.unsignedIntValue;
        char c[5] = { (char)(f >> 24), (char)(f >> 16), (char)(f >> 8), (char)f, 0 };
        for (int i = 0; i < 4; i++) if (c[i] < 32 || c[i] > 126 || c[i] == '"' || c[i] == '\\') c[i] = '?';
        [parts addObject:[NSString stringWithFormat:@"\"%s\"", c]];
    }
    return [NSString stringWithFormat:@"[%@]", [parts componentsJoinedByString:@","]];
}
// Configurations whose model download is running, kept alive until VideoToolbox answers.
static NSMutableSet *downloads;
#endif

int kr_upscale_support(int w, int h, int ow, int oh, int engine, char *json, int size) {
    NSString *text = nil;
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        double f = 0, fv = 0, fi = 0, ff = 0;
        int chosen = -1;
        kr_tiles tf = { 0, 0, 0, 0 };
        id c = choose(engine, w, h, ow, oh, &chosen, &f, NULL);
        BOOL sr = VTSuperResolutionScalerConfiguration.isSupported, fast = VTLowLatencySuperResolutionScalerConfiguration.isSupported;
        id cv = sr ? make_config(KR_UP_AI_VIDEO, w, h, ow, oh, &fv, NULL) : nil;
        id ci = sr ? make_config(KR_UP_AI_IMAGE, w, h, ow, oh, &fi, NULL) : nil;
        id cf = fast ? make_config(KR_UP_AI_FAST, w, h, ow, oh, &ff, &tf) : nil;
        NSString *model = @"none";
        float pct = 0;
        if (c) {
            int s = model_status(c);
            model = s == 2 ? @"ready" : s == 1 ? @"downloading" : @"download-required";
            pct = [c isKindOfClass:VTSuperResolutionScalerConfiguration.class]
                ? ((VTSuperResolutionScalerConfiguration *)c).configurationModelPercentageAvailable : 1;
        }
        NSString *formats = c ? formats_json([c frameSupportedPixelFormats]) : @"[]";
        CMVideoDimensions mx = fast ? VTLowLatencySuperResolutionScalerConfiguration.maximumDimensions : (CMVideoDimensions){0, 0};
        CMVideoDimensions mn = fast ? VTLowLatencySuperResolutionScalerConfiguration.minimumDimensions : (CMVideoDimensions){0, 0};
        text = [NSString stringWithFormat:
            @"{\"os26\":1,\"engine\":\"%s\",\"engine_id\":%d,\"scale\":%g,\"model\":\"%@\",\"model_pct\":%.3f,"
            "\"video\":{\"supported\":%d,\"factors\":%@,\"fits\":%d,\"scale\":%g},"
            "\"image\":{\"supported\":%d,\"factors\":%@,\"fits\":%d,\"scale\":%g},"
            "\"fast\":{\"supported\":%d,\"factors\":%@,\"fits\":%d,\"scale\":%g,\"max\":\"%dx%d\",\"min\":\"%dx%d\",\"tiles\":\"%dx%d\"},"
            "\"formats\":%@}",
            engine_word(chosen), chosen, f, model, pct,
            sr, sr ? factors_json(VTSuperResolutionScalerConfiguration.supportedScaleFactors) : @"[]", cv != nil, fv,
            sr, sr ? factors_json(VTSuperResolutionScalerConfiguration.supportedScaleFactors) : @"[]", ci != nil, fi,
            fast, fast ? factors_json([VTLowLatencySuperResolutionScalerConfiguration supportedScaleFactorsForFrameWidth:(tf.cols ? tf.tw : w)
                                                                                                            frameHeight:(tf.rows ? tf.th : h)]) : @"[]",
            cf != nil, ff, mx.width, mx.height, mn.width, mn.height, tf.cols ? tf.cols : 1, tf.rows ? tf.rows : 1, formats];
    }
#endif
    if (!text) text = @"{\"os26\":0,\"engine\":\"none\",\"engine_id\":-1,\"scale\":0,\"model\":\"none\",\"model_pct\":0,"
                       "\"why\":\"AI upscaling needs iOS 26\"}";
    const char *s = text.UTF8String;
    int n = (int)strlen(s);
    if (n >= size) return -1;
    memcpy(json, s, (size_t)n + 1);
    return n;
}

int kr_upscale_model(int w, int h, int ow, int oh, int engine, int start, float *pct) {
    if (pct) *pct = 0;
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        double f = 0;
        int chosen = -1;
        id c = choose(engine, w, h, ow, oh, &chosen, &f, NULL);
        if (!c) return -1;
        int s = model_status(c);
        BOOL sr = [c isKindOfClass:VTSuperResolutionScalerConfiguration.class];
        if (pct) *pct = sr ? ((VTSuperResolutionScalerConfiguration *)c).configurationModelPercentageAvailable : 1;
        if (s == 0 && start && sr) {
            VTSuperResolutionScalerConfiguration *keep = c;
            @synchronized (VTSuperResolutionScalerConfiguration.class) {
                if (!downloads) downloads = [NSMutableSet set];
                [downloads addObject:keep];
            }
            kr_remux_note("upscale: model download started (%s, %dx%d)", engine_word(chosen), w, h);
            [keep downloadConfigurationModelWithCompletionHandler:^(NSError *error) {
                if (error) kr_remux_note("upscale: model download failed: %s", error.localizedDescription.UTF8String ?: "unknown");
                else kr_remux_note("upscale: model downloaded");
                @synchronized (VTSuperResolutionScalerConfiguration.class) { [downloads removeObject:keep]; }
            }];
            return 1;
        }
        return s;
    }
#endif
    (void)w; (void)h; (void)ow; (void)oh; (void)engine; (void)start;
    return -1;
}

static CVPixelBufferPoolRef make_pool(NSDictionary *attributes) {
    CVPixelBufferPoolRef pool = NULL;
    if (!attributes || CVPixelBufferPoolCreate(kCFAllocatorDefault, NULL, (__bridge CFDictionaryRef)attributes, &pool) != kCVReturnSuccess)
        return NULL;
    return pool;
}

kr_upscale *kr_upscale_open(int w, int h, int ow, int oh, int engine, char *err, int errlen) {
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        double f = 0;
        int chosen = -1;
        kr_tiles t = { 0, 0, 0, 0 };
        id c = choose(engine, w, h, ow, oh, &chosen, &f, &t);
        if (!c) { seterr(err, errlen, [NSString stringWithFormat:@"AI upscaling is not available on this device for %dx%d", w, h]); return NULL; }
        if (model_status(c) != 2) { seterr(err, errlen, @"The AI upscaling model is not on this iPhone yet"); return NULL; }
        VTFrameProcessor *processor = [[VTFrameProcessor alloc] init];
        NSError *error = nil;
        if (![processor startSessionWithConfiguration:c error:&error]) {
            seterr(err, errlen, [NSString stringWithFormat:@"AI upscaling could not start: %@", error.localizedDescription ?: @"unknown"]);
            return NULL;
        }
        kr_upscale *u = calloc(1, sizeof *u);
        if (!u) { [processor endSession]; seterr(err, errlen, @"out of memory"); return NULL; }
        u->processor = (void *)CFBridgingRetain(processor);
        u->config = (void *)CFBridgingRetain(c);
        u->engine = chosen; u->w = w; u->h = h;
        u->ow = (int)lround(w * f) & ~1; u->oh = (int)lround(h * f) & ~1;
        u->f = f;
        u->in_pool = make_pool([c sourcePixelBufferAttributes]);
        u->out_pool = make_pool([c destinationPixelBufferAttributes]);
        if (!u->in_pool || !u->out_pool || VTPixelTransferSessionCreate(kCFAllocatorDefault, &u->xfer) != noErr) {
            kr_upscale_close(u); seterr(err, errlen, @"AI upscaling buffers could not be made"); return NULL;
        }
        if (t.cols) {
            u->cols = t.cols; u->rows = t.rows; u->tw = t.tw; u->th = t.th;
            NSDictionary *(^rgba)(int, int) = ^NSDictionary *(int bw, int bh) {
                return @{(id)kCVPixelBufferPixelFormatTypeKey: @(kCVPixelFormatType_64RGBAHalf), (id)kCVPixelBufferWidthKey: @(bw),
                         (id)kCVPixelBufferHeightKey: @(bh), (id)kCVPixelBufferIOSurfacePropertiesKey: @{},
                         (id)kCVPixelBufferMetalCompatibilityKey: @YES};
            };
            u->tile_pool = make_pool(rgba((int)lround(t.tw * f), (int)lround(t.th * f)));
            u->big_pool = make_pool(rgba(u->ow, u->oh));
            if (!u->tile_pool || !u->big_pool || VTPixelTransferSessionCreate(kCFAllocatorDefault, &u->crop) != noErr ||
                VTSessionSetProperty(u->crop, kVTPixelTransferPropertyKey_ScalingMode, kVTScalingMode_CropSourceToCleanAperture) != noErr) {
                kr_upscale_close(u); seterr(err, errlen, @"AI upscaling tile buffers could not be made"); return NULL;
            }
        }
        // Read the engine's real output size from one destination buffer (its attributes decide, not our arithmetic).
        CVPixelBufferRef probe = NULL;
        if (!u->cols && CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->out_pool, &probe) == kCVReturnSuccess && probe) {
            u->ow = (int)CVPixelBufferGetWidth(probe); u->oh = (int)CVPixelBufferGetHeight(probe);
            CVPixelBufferRelease(probe);
        }
        if (u->cols)
            snprintf(u->name, sizeof u->name, "AI super resolution (low-latency model, %gx, %dx%d tiles of %dx%d)", f, u->cols, u->rows, u->tw, u->th);
        else
            snprintf(u->name, sizeof u->name, "AI super resolution (%s, %gx)",
                     chosen == KR_UP_AI_VIDEO ? "video model" : chosen == KR_UP_AI_IMAGE ? "image model" : "low-latency model", f);
        kr_remux_note("upscale: %s, %dx%d -> %dx%d", u->name, w, h, u->ow, u->oh);
        return u;
    }
#endif
    (void)w; (void)h; (void)ow; (void)oh; (void)engine;
    seterr(err, errlen, @"AI upscaling needs iOS 26");
    return NULL;
}

#ifdef KR_SR
// One tile: the source's x0,y0 tw x th window -> the engine -> RGBA half float (tw*f x th*f), retained in *out.
static int tile_once(kr_upscale *u, CVPixelBufferRef src, int x0, int y0, double seconds, CVPixelBufferRef *out, NSString **why) API_AVAILABLE(ios(26.0)) {
    *out = NULL;
    CVPixelBufferRef in = NULL, dst = NULL, rgba = NULL;
    // The tile is the source's clean aperture (its offsets count from the picture's centre); the crop session's scaling
    // mode is CropSourceToCleanAperture, so the transfer cuts exactly that window (same size: no scaling).
    NSDictionary *aperture = @{(id)kCVImageBufferCleanApertureWidthKey: @(u->tw), (id)kCVImageBufferCleanApertureHeightKey: @(u->th),
        (id)kCVImageBufferCleanApertureHorizontalOffsetKey: @((x0 + u->tw / 2.0) - u->w / 2.0),
        (id)kCVImageBufferCleanApertureVerticalOffsetKey: @((y0 + u->th / 2.0) - u->h / 2.0)};
    CVBufferSetAttachment(src, kCVImageBufferCleanApertureKey, (__bridge CFDictionaryRef)aperture, kCVAttachmentMode_ShouldNotPropagate);
    if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->in_pool, &in) != kCVReturnSuccess || !in) { *why = @"no tile input buffer"; return -1; }
    if (VTPixelTransferSessionTransferImage(u->crop, src, in) != noErr) { CVPixelBufferRelease(in); *why = @"tile could not be cut"; return -1; }
    if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->out_pool, &dst) != kCVReturnSuccess || !dst) {
        CVPixelBufferRelease(in); *why = @"no tile output buffer"; return -1;
    }
    BOOL ok = NO;
    NSError *error = nil;
    @autoreleasepool {
        CMTime t = CMTimeMakeWithSeconds(seconds, 90000);
        VTFrameProcessorFrame *source = [[VTFrameProcessorFrame alloc] initWithBuffer:in presentationTimeStamp:t];
        VTFrameProcessorFrame *destination = [[VTFrameProcessorFrame alloc] initWithBuffer:dst presentationTimeStamp:t];
        id params = source && destination ? [[VTLowLatencySuperResolutionScalerParameters alloc] initWithSourceFrame:source destinationFrame:destination] : nil;
        if (params) ok = [(__bridge VTFrameProcessor *)u->processor processWithParameters:params error:&error];
        if (!ok) *why = [NSString stringWithFormat:@"AI upscaling failed on a tile: %@", error.localizedDescription ?: @"frame not accepted"];
    }
    CVPixelBufferRelease(in);
    if (!ok) { CVPixelBufferRelease(dst); return -1; }
    if (CVPixelBufferGetPixelFormatType(dst) == kCVPixelFormatType_64RGBAHalf && !CVPixelBufferIsPlanar(dst)) { *out = dst; return 0; }
    if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->tile_pool, &rgba) != kCVReturnSuccess || !rgba ||
        VTPixelTransferSessionTransferImage(u->xfer, dst, rgba) != noErr) {
        CVPixelBufferRelease(dst); if (rgba) CVPixelBufferRelease(rgba); *why = @"tile result could not be read"; return -1;
    }
    CVPixelBufferRelease(dst);
    *out = rgba;
    return 0;
}

// The tiled picture: each tile's middle part (without the margin it shares with its neighbours) into one buffer.
static int tiled_frame(kr_upscale *u, CVPixelBufferRef src, double seconds, void **out, char *err, int errlen) API_AVAILABLE(ios(26.0)) {
    int w = u->w, h = u->h;
    double f = u->f;
    int iw = ((((w + u->cols - 1) / u->cols)) + 1) & ~1, ih = ((((h + u->rows - 1) / u->rows)) + 1) & ~1;
    CVPixelBufferRef big = NULL;
    if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->big_pool, &big) != kCVReturnSuccess || !big) {
        seterr(err, errlen, @"upscale: no buffer for the joined picture"); return -1;
    }
    CVPixelBufferLockBaseAddress(big, 0);
    uint8_t *bb = CVPixelBufferGetBaseAddress(big);
    size_t brow = CVPixelBufferGetBytesPerRow(big);
    int bw = (int)CVPixelBufferGetWidth(big), bh = (int)CVPixelBufferGetHeight(big);
    for (int r = 0; r < u->rows; r++) {
        for (int c = 0; c < u->cols; c++) {
            int ix = c * iw, iy = r * ih;
            if (ix >= w || iy >= h) continue;
            int pw = ix + iw > w ? w - ix : iw, ph = iy + ih > h ? h - iy : ih;
            int x0 = ix - KR_TILE_MARGIN, y0 = iy - KR_TILE_MARGIN;
            if (x0 > w - u->tw) x0 = w - u->tw;
            if (y0 > h - u->th) y0 = h - u->th;
            if (x0 < 0) x0 = 0;
            if (y0 < 0) y0 = 0;
            CVPixelBufferRef tile = NULL;
            NSString *why = nil;
            if (tile_once(u, src, x0, y0, seconds, &tile, &why) < 0) {
                CVBufferRemoveAttachment(src, kCVImageBufferCleanApertureKey);
                CVPixelBufferUnlockBaseAddress(big, 0); CVPixelBufferRelease(big); seterr(err, errlen, why ?: @"tile failed"); return -1;
            }
            int dx = c == 0 ? 0 : (int)lround(ix * f), dy = r == 0 ? 0 : (int)lround(iy * f);
            int ex = (c == u->cols - 1 || ix + pw >= w) ? bw : (int)lround((ix + pw) * f);
            int ey = (r == u->rows - 1 || iy + ph >= h) ? bh : (int)lround((iy + ph) * f);
            int sx = dx - (int)lround(x0 * f), sy = dy - (int)lround(y0 * f);
            CVPixelBufferLockBaseAddress(tile, kCVPixelBufferLock_ReadOnly);
            const uint8_t *tb = CVPixelBufferGetBaseAddress(tile);
            size_t trow = CVPixelBufferGetBytesPerRow(tile);
            int tw = (int)CVPixelBufferGetWidth(tile), th = (int)CVPixelBufferGetHeight(tile);
            if (sx < 0) sx = 0;
            if (sy < 0) sy = 0;
            int cw = ex - dx, chh = ey - dy;
            if (sx + cw > tw) cw = tw - sx;
            if (sy + chh > th) chh = th - sy;
            for (int y = 0; y < chh && tb && bb; y++)
                memcpy(bb + (size_t)(dy + y) * brow + (size_t)dx * 8, tb + (size_t)(sy + y) * trow + (size_t)sx * 8, (size_t)cw * 8);
            CVPixelBufferUnlockBaseAddress(tile, kCVPixelBufferLock_ReadOnly);
            CVPixelBufferRelease(tile);
        }
    }
    CVPixelBufferUnlockBaseAddress(big, 0);
    CVBufferRemoveAttachment(src, kCVImageBufferCleanApertureKey);
    CVBufferPropagateAttachments(src, big);   // colour tags travel with the picture
    *out = big;
    return 0;
}
#endif

int kr_upscale_frame(kr_upscale *u, void *src, double seconds, int sequential, void **out, char *err, int errlen) {
    if (out) *out = NULL;
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        if (!u || !src || !out) { seterr(err, errlen, @"upscale: nothing to do"); return -1; }
        if (u->cols) {
            double began = now_ms();
            int r = tiled_frame(u, (CVPixelBufferRef)src, seconds, out, err, errlen);
            if (r == 0) { u->busy_ms += now_ms() - began; u->frames++; }
            return r;
        }
        double began = now_ms();
        CVPixelBufferRef in = NULL, dst = NULL;
        if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->in_pool, &in) != kCVReturnSuccess || !in) {
            seterr(err, errlen, @"upscale: no input buffer"); return -1;
        }
        // The decoder's picture into the engine's own format (8-bit or 10-bit 4:2:0 as it asks; same size).
        if (VTPixelTransferSessionTransferImage(u->xfer, (CVPixelBufferRef)src, in) != noErr) {
            CVPixelBufferRelease(in); seterr(err, errlen, @"upscale: picture could not be handed to the engine"); return -1;
        }
        if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->out_pool, &dst) != kCVReturnSuccess || !dst) {
            CVPixelBufferRelease(in); seterr(err, errlen, @"upscale: no output buffer"); return -1;
        }
        BOOL ok = NO;
        NSError *error = nil;
        @autoreleasepool {
            CMTime t = CMTimeMakeWithSeconds(seconds, 90000);
            VTFrameProcessorFrame *source = [[VTFrameProcessorFrame alloc] initWithBuffer:in presentationTimeStamp:t];
            VTFrameProcessorFrame *destination = [[VTFrameProcessorFrame alloc] initWithBuffer:dst presentationTimeStamp:t];
            id params = nil;
            if (source && destination && u->engine == KR_UP_AI_FAST) {
                params = [[VTLowLatencySuperResolutionScalerParameters alloc] initWithSourceFrame:source destinationFrame:destination];
            } else if (source && destination) {
                BOOL chain = sequential && u->prev_in && u->prev_out && u->engine == KR_UP_AI_VIDEO;
                CMTime pt = CMTimeMakeWithSeconds(u->prev_t, 90000);
                VTFrameProcessorFrame *prev = chain ? [[VTFrameProcessorFrame alloc] initWithBuffer:u->prev_in presentationTimeStamp:pt] : nil;
                VTFrameProcessorFrame *prevOut = chain ? [[VTFrameProcessorFrame alloc] initWithBuffer:u->prev_out presentationTimeStamp:pt] : nil;
                params = [[VTSuperResolutionScalerParameters alloc] initWithSourceFrame:source previousFrame:prev previousOutputFrame:prevOut
                    opticalFlow:nil
                 submissionMode:chain ? VTSuperResolutionScalerParametersSubmissionModeSequential : VTSuperResolutionScalerParametersSubmissionModeRandom
               destinationFrame:destination];
            }
            if (params) ok = [(__bridge VTFrameProcessor *)u->processor processWithParameters:params error:&error];
            if (!ok) seterr(err, errlen, [NSString stringWithFormat:@"AI upscaling failed: %@",
                                          error.localizedDescription ?: (params ? @"unknown" : @"frame not accepted")]);
        }
        if (!ok) { CVPixelBufferRelease(in); CVPixelBufferRelease(dst); return -1; }
        CVBufferPropagateAttachments((CVPixelBufferRef)src, dst);   // colour tags travel with the picture
        if (u->prev_in) CVPixelBufferRelease(u->prev_in);
        if (u->prev_out) CVPixelBufferRelease(u->prev_out);
        u->prev_in = in; u->prev_out = CVPixelBufferRetain(dst); u->prev_t = seconds;
        *out = dst;
        u->busy_ms += now_ms() - began;
        u->frames++;
        return 0;
    }
#endif
    (void)u; (void)src; (void)seconds; (void)sequential;
    seterr(err, errlen, @"AI upscaling needs iOS 26");
    return -1;
}

int kr_upscale_out_width(const kr_upscale *u) { return u ? u->ow : 0; }
int kr_upscale_out_height(const kr_upscale *u) { return u ? u->oh : 0; }
int kr_upscale_engine(const kr_upscale *u) { return u ? u->engine : -1; }
const char *kr_upscale_name(const kr_upscale *u) { return u ? u->name : "none"; }
double kr_upscale_busy_ms(const kr_upscale *u) { return u ? u->busy_ms : 0; }
long kr_upscale_frames(const kr_upscale *u) { return u ? u->frames : 0; }

void kr_upscale_close(kr_upscale *u) {
    if (!u) return;
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        if (u->processor) {
            VTFrameProcessor *p = (VTFrameProcessor *)CFBridgingRelease(u->processor);
            [p endSession];
            u->processor = NULL;
        }
    }
#endif
    if (u->processor) CFRelease(u->processor);
    if (u->config) CFRelease(u->config);
    if (u->xfer) { VTPixelTransferSessionInvalidate(u->xfer); CFRelease(u->xfer); }
    if (u->crop) { VTPixelTransferSessionInvalidate(u->crop); CFRelease(u->crop); }
    if (u->tile_pool) CVPixelBufferPoolRelease(u->tile_pool);
    if (u->big_pool) CVPixelBufferPoolRelease(u->big_pool);
    if (u->in_pool) CVPixelBufferPoolRelease(u->in_pool);
    if (u->out_pool) CVPixelBufferPoolRelease(u->out_pool);
    if (u->prev_in) CVPixelBufferRelease(u->prev_in);
    if (u->prev_out) CVPixelBufferRelease(u->prev_out);
    free(u);
}

// Battery and charging come from UIKit on the main thread; the latest values are kept here for any thread.
static _Atomic float battery = -1;
static atomic_int charging = -1;
int kr_device_state(char *json, int size) {
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        dispatch_async(dispatch_get_main_queue(), ^{ UIDevice.currentDevice.batteryMonitoringEnabled = YES; });
    });
    dispatch_async(dispatch_get_main_queue(), ^{
        UIDevice *d = UIDevice.currentDevice;
        atomic_store(&battery, d.batteryLevel);
        UIDeviceBatteryState s = d.batteryState;
        atomic_store(&charging, s == UIDeviceBatteryStateUnknown ? -1 : (s == UIDeviceBatteryStateCharging || s == UIDeviceBatteryStateFull));
    });
    NSProcessInfoThermalState t = NSProcessInfo.processInfo.thermalState;
    const char *word = t == NSProcessInfoThermalStateNominal ? "nominal" : t == NSProcessInfoThermalStateFair ? "fair"
                     : t == NSProcessInfoThermalStateSerious ? "serious" : t == NSProcessInfoThermalStateCritical ? "critical" : "unknown";
    int n = snprintf(json, (size_t)size, "{\"battery\":%.3f,\"charging\":%d,\"thermal\":\"%s\",\"thermal_id\":%d,\"low_power\":%d}",
                     atomic_load(&battery), atomic_load(&charging), word, (int)t, NSProcessInfo.processInfo.lowPowerModeEnabled ? 1 : 0);
    return n < size ? n : -1;
}
