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

struct kr_upscale {
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

// The configuration for one engine, nil when it does not take this size on this phone.
static id make_config(int engine, int w, int h, int ow, int oh, double *factor) API_AVAILABLE(ios(26.0)) {
    *factor = 0;
    double need = needed(w, h, ow, oh);
    if (engine == KR_UP_AI_VIDEO || engine == KR_UP_AI_IMAGE) {
        if (!VTSuperResolutionScalerConfiguration.isSupported) return nil;
        double f = pick_factor(VTSuperResolutionScalerConfiguration.supportedScaleFactors, need);
        if (f < 1.5) return nil;
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
        if (w > mx.width || h > mx.height || w < mn.width || h < mn.height) return nil;
        double f = pick_factor([VTLowLatencySuperResolutionScalerConfiguration supportedScaleFactorsForFrameWidth:w frameHeight:h], need);
        if (f < 1.2) return nil;
        VTLowLatencySuperResolutionScalerConfiguration *c =
            [[VTLowLatencySuperResolutionScalerConfiguration alloc] initWithFrameWidth:w frameHeight:h scaleFactor:(float)f];
        if (c) *factor = f;
        return c;
    }
    return nil;
}
// AUTO: the video model (uses neighbouring frames), then the image model, then the low-latency one.
static id choose(int want, int w, int h, int ow, int oh, int *engine, double *factor) API_AVAILABLE(ios(26.0)) {
    int order[3] = { KR_UP_AI_VIDEO, KR_UP_AI_IMAGE, KR_UP_AI_FAST };
    for (int i = 0; i < 3; i++) {
        if (want != KR_UP_AUTO && want != order[i]) continue;
        id c = make_config(order[i], w, h, ow, oh, factor);
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
        id c = choose(engine, w, h, ow, oh, &chosen, &f);
        BOOL sr = VTSuperResolutionScalerConfiguration.isSupported, fast = VTLowLatencySuperResolutionScalerConfiguration.isSupported;
        id cv = sr ? make_config(KR_UP_AI_VIDEO, w, h, ow, oh, &fv) : nil;
        id ci = sr ? make_config(KR_UP_AI_IMAGE, w, h, ow, oh, &fi) : nil;
        id cf = fast ? make_config(KR_UP_AI_FAST, w, h, ow, oh, &ff) : nil;
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
            "\"fast\":{\"supported\":%d,\"factors\":%@,\"fits\":%d,\"scale\":%g,\"max\":\"%dx%d\",\"min\":\"%dx%d\"},"
            "\"formats\":%@}",
            engine_word(chosen), chosen, f, model, pct,
            sr, sr ? factors_json(VTSuperResolutionScalerConfiguration.supportedScaleFactors) : @"[]", cv != nil, fv,
            sr, sr ? factors_json(VTSuperResolutionScalerConfiguration.supportedScaleFactors) : @"[]", ci != nil, fi,
            fast, fast ? factors_json([VTLowLatencySuperResolutionScalerConfiguration supportedScaleFactorsForFrameWidth:w frameHeight:h]) : @"[]",
            cf != nil, ff, mx.width, mx.height, mn.width, mn.height, formats];
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
        id c = choose(engine, w, h, ow, oh, &chosen, &f);
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
        id c = choose(engine, w, h, ow, oh, &chosen, &f);
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
        u->in_pool = make_pool([c sourcePixelBufferAttributes]);
        u->out_pool = make_pool([c destinationPixelBufferAttributes]);
        if (!u->in_pool || !u->out_pool || VTPixelTransferSessionCreate(kCFAllocatorDefault, &u->xfer) != noErr) {
            kr_upscale_close(u); seterr(err, errlen, @"AI upscaling buffers could not be made"); return NULL;
        }
        // Read the engine's real output size from one destination buffer (its attributes decide, not our arithmetic).
        CVPixelBufferRef probe = NULL;
        if (CVPixelBufferPoolCreatePixelBuffer(kCFAllocatorDefault, u->out_pool, &probe) == kCVReturnSuccess && probe) {
            u->ow = (int)CVPixelBufferGetWidth(probe); u->oh = (int)CVPixelBufferGetHeight(probe);
            CVPixelBufferRelease(probe);
        }
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

int kr_upscale_frame(kr_upscale *u, void *src, double seconds, int sequential, void **out, char *err, int errlen) {
    if (out) *out = NULL;
#ifdef KR_SR
    if (@available(iOS 26.0, *)) {
        if (!u || !src || !out) { seterr(err, errlen, @"upscale: nothing to do"); return -1; }
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
