// kr_upscale (r48, DEC-039/DEC-040): AI upscaling for prepared copies. Apple's VideoToolbox frame processor
// (VTFrameProcessor with VTSuperResolutionScalerConfiguration, iOS 26+) enlarges each decoded picture; kr_video then
// fits it to the exact target size (VTPixelTransferSession) and encodes HEVC. Only the iPhone build has an engine
// (kr_upscale.m); every other build gets kr_upscale_stub.c, which reports "not available" so the caller never
// pretends a plain resize is AI. Kodi iOS code.
#ifndef KR_UPSCALE_H
#define KR_UPSCALE_H
#ifdef __cplusplus
extern "C" {
#endif

// Engines. AUTO picks the first AI engine that takes the source size (video model, then image model, then the
// low-latency model). LANCZOS is a plain Lanczos resize on the CPU (kr_video, libswscale): named as such everywhere,
// used by host tests and the measurement build's comparison, never offered to the person as "AI".
enum {
    KR_UP_AUTO = 0,
    KR_UP_LANCZOS = 1,
    KR_UP_AI_VIDEO = 2,   // VTSuperResolutionScaler, video model (temporal: uses the previous frame and output)
    KR_UP_AI_IMAGE = 3,   // VTSuperResolutionScaler, image model (each frame alone)
    KR_UP_AI_FAST = 4,    // VTLowLatencySuperResolutionScaler (lightweight, made for video calls)
};

typedef struct kr_upscale kr_upscale;

// What this device can do for a w x h source and an ow x oh target, as JSON (no paths):
// {"os26":1,"engine":"ai-image","engine_id":3,"scale":2,"model":"ready","model_pct":1.0,
//  "video":{"supported":1,"factors":[2,4],"fits":0},"image":{...},"fast":{"supported":1,"factors":[1.5,2],
//  "max":"1920x1080","min":"..","fits":1},"formats":["420v"]}
// engine is "none" when no AI engine takes this size; "model" is ready | downloading | download-required | none.
// Returns the length written, negative when json is too small.
int kr_upscale_support(int w, int h, int ow, int oh, int engine, char *json, int size);
// The engine's model: 2 ready, 1 downloading, 0 download required, -1 no AI engine for this size. start=1 asks
// VideoToolbox to download it (returns at once; poll again). pct receives 0..1 when not NULL.
int kr_upscale_model(int w, int h, int ow, int oh, int engine, int start, float *pct);

// Opens an AI engine for w x h -> at least ow x oh (the engine's own factor; kr_video fits the result). The model must
// be ready (kr_upscale_model): opening never downloads. NULL with a reason in err when it cannot.
kr_upscale *kr_upscale_open(int w, int h, int ow, int oh, int engine, char *err, int errlen);
// One picture: src is a CVPixelBufferRef (any format VideoToolbox can transfer), seconds its presentation time.
// sequential=0 at a unit's first frame (the engine clears its history). *out receives a retained CVPixelBufferRef at
// kr_upscale_out_width/height; the caller releases it. 0 success, -1 failure with a reason.
int kr_upscale_frame(kr_upscale *u, void *src, double seconds, int sequential, void **out, char *err, int errlen);
int kr_upscale_out_width(const kr_upscale *u);
int kr_upscale_out_height(const kr_upscale *u);
int kr_upscale_engine(const kr_upscale *u);
// "AI super resolution (image model, 2x)": for the log and the copy's metadata.
const char *kr_upscale_name(const kr_upscale *u);
// Milliseconds spent inside the engine so far, and pictures done (measurement).
double kr_upscale_busy_ms(const kr_upscale *u);
long kr_upscale_frames(const kr_upscale *u);
void kr_upscale_close(kr_upscale *u);

// The phone right now, as JSON: {"battery":0.83,"charging":1,"thermal":"nominal","thermal_id":0,"low_power":0}.
// battery is -1 until iOS reports it (monitoring is switched on at the first call). Any thread.
int kr_device_state(char *json, int size);
#ifdef __cplusplus
}
#endif
#endif
