// Session + loopback HTTP server for the AirPlay remuxer. POSIX sockets, one thread per connection, bound to
// 127.0.0.1 on a port the system picks (no port conflicts with Elementum 65220 or Kodi's web server).
// r8: a third-party AirPlay receiver (TV, User-Agent "... MFi_AirPlay_Device ...") gets the picture converted to H.264
// when the source video is not H.264, while the phone and an Apple TV keep the copy; segments are produced on parallel
// lanes (video copy, converted video, audio copy and each AAC bridge have their own demuxer and lock), inits and
// recent segments are cached, and the next two segments of a rendition are made ahead in the background.
#include "kr_remux.h"
#include "kr_audio.h"
#include "kr_hls.h"
#include "kr_source.h"
#include "kr_video.h"
#include "kr_subs.h"
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include <libavformat/avformat.h>

#ifndef MSG_NOSIGNAL
#define MSG_NOSIGNAL 0
#endif
#define SEG_SECONDS 6.0
#define MAX_TRACKS 64
// r8: renditions (cache keys and production lanes): the copied video, the converted video, audio by source index.
enum { R_VCOPY = 0, R_VCOMPAT = 1, R_AUDIO = 2, NREND = R_AUDIO + MAX_TRACKS };
#define PF_DEPTH_VIDEO 3  // r11: video segments made ahead after one is served
#define PF_DEPTH_AUDIO 6  // r11: audio is cheap (a copy or one AAC encode): kept well ahead so it never waits
#define PF_DEPTH(rend) ((rend) >= R_AUDIO ? PF_DEPTH_AUDIO : PF_DEPTH_VIDEO)
#define PF_WORKERS 3    // background producers (r11: video, audio and a spare, so audio never queues behind video)
#define PF_QUEUE 32
#define CACHE_SLOTS 24
#define CACHE_BYTES (64u << 20)  // made and recently served media segments (inits are kept apart, a few KB each)

typedef struct {
    kr_source *src;
    kr_audio *audio;
    int index;
    pthread_mutex_t lock;
} bridge;

static struct {
    pthread_mutex_t lock;     // session start/stop
    pthread_mutex_t gm_lock;  // gm_stream is single-threaded
    atomic_int state;
    char message[256];
    char url[4096];
    kr_source *src;
    gm_stream *gm;
    bridge bridges[MAX_TRACKS];
    int nbridges;
    int listen_fd, port;
    pthread_t accept_thread;
    atomic_int stopping, active;
    char base[128];
    char token[40];
    atomic_int served_video, served_audio;
    atomic_int served_ext_video, served_ext_audio;  // r8: to receivers other than the phone's own player
    char vcodec[64];  // r6: the variant's video CODECS value ("hvc1.2.4.L120.90")
    int compat;       // r7: /video/ is the picture converted to H.264 (kr_video), not copied
    int vindex;       // r7: the source video stream converted in compat mode
    kr_source *vsrc;  // r7: the converter's own connection to the source, opened on first use
    kr_video *video;
    pthread_mutex_t vlock;  // one conversion at a time (one hardware encoder session; battery)
    // r8
    pthread_mutex_t agm_lock;  // the audio-copy / subtitle demuxer: its own connection, works while video is made
    kr_source *asrc;
    gm_stream *agm;
    int agm_failed;            // the second connection could not open: audio copy shares the video's demuxer
    int routes[MAX_TRACKS];    // kr_audio_route per source index, fixed at start (no demuxer access per request)
    int compat_ok;             // a third-party receiver can be given the converted picture (source video not H.264)
    char *master_copy, *master_compat;  // fixed at start; master_compat points /cvideo/ at the converted picture
    atomic_int compat_clients, prefetched;
    atomic_int vlogged;        // r11: converted segments logged this session
    // r10: subtitles burned into the converted picture, fixed at start (the session's R_VCOMPAT cache holds only
    // segments with them: another choice is a new session, so the cache key needs no burn field)
    int burn_index;            // source text subtitle stream, -1 none
    // r11: the WebVTT demuxer: its own connection and lock (r10 shared the audio demuxer: a subtitle read of 5-13 s held
    // the audio lane and the TV hung up on audio seg8 after 5.5 s). A request that finds it busy gets an empty cue file.
    pthread_mutex_t sgm_lock;
    kr_source *ssrc;
    gm_stream *sgm;
    int sgm_failed;
    char burn_file[1024];      // external subtitle file when burn_index < 0, "" none
} S = { .lock = PTHREAD_MUTEX_INITIALIZER, .gm_lock = PTHREAD_MUTEX_INITIALIZER, .vlock = PTHREAD_MUTEX_INITIALIZER,
        .agm_lock = PTHREAD_MUTEX_INITIALIZER, .sgm_lock = PTHREAD_MUTEX_INITIALIZER, .listen_fd = -1, .vindex = -1, .burn_index = -1 };

// r10: the subtitle choice for the next kr_remux_start (Kodi's selection, from Python).
static struct { pthread_mutex_t lock; int ordinal; char file[1024]; char lang[16]; } SUBS = { PTHREAD_MUTEX_INITIALIZER, -2, "", "" };
void kr_remux_set_subtitles(int ordinal, const char *file, const char *lang) {
    pthread_mutex_lock(&SUBS.lock);
    SUBS.ordinal = ordinal < -2 ? -1 : ordinal;
    snprintf(SUBS.file, sizeof SUBS.file, "%s", file ? file : "");
    snprintf(SUBS.lang, sizeof SUBS.lang, "%s", lang ? lang : "");
    pthread_mutex_unlock(&SUBS.lock);
}
int kr_remux_burn_track(void) { return S.burn_index >= 0 ? S.burn_index : S.burn_file[0] ? -2 : -1; }

static void set_message(const char *m) { snprintf(S.message, sizeof S.message, "%s", m ? m : ""); }

// -- r6 log: what the receiver asked for and how it went, for kodi.log (kr_remux_log) --
#define LOG_LINES 128
#define LOG_WIDTH 240
static struct {
    pthread_mutex_t lock;
    char lines[LOG_LINES][LOG_WIDTH];
    unsigned long written, read;  // line counters; written - read lines are waiting
    char agents[4][160];
} L = { .lock = PTHREAD_MUTEX_INITIALIZER };

static double now_ms(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000.0 + t.tv_nsec / 1e6;
}

static void log_line(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void log_line(const char *fmt, ...) {
    char line[LOG_WIDTH];
    va_list ap; va_start(ap, fmt); vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
    for (char *c = line; *c; c++) if (*c == '\n' || *c == '\r') *c = ' ';
    pthread_mutex_lock(&L.lock);
    snprintf(L.lines[L.written % LOG_LINES], LOG_WIDTH, "%s", line);
    L.written++;
    if (L.written - L.read > LOG_LINES) L.read = L.written - LOG_LINES;  // oldest lines dropped
    pthread_mutex_unlock(&L.lock);
}

// Each distinct User-Agent once per session: names the receiver (AppleCoreMedia on the phone, the TV's own player).
static void log_agent(const char *ua) {
    if (!ua || !*ua) return;
    pthread_mutex_lock(&L.lock);
    int seen = 0, slot = -1;
    for (int i = 0; i < 4; i++) {
        if (!strncmp(L.agents[i], ua, sizeof L.agents[i] - 1)) { seen = 1; break; }
        if (slot < 0 && !L.agents[i][0]) slot = i;
    }
    if (!seen && slot >= 0) snprintf(L.agents[slot], sizeof L.agents[slot], "%s", ua);
    pthread_mutex_unlock(&L.lock);
    if (!seen && slot >= 0) log_line("client: %.200s", ua);
}

int kr_remux_log(char *buf, int len) {
    if (!buf || len <= 0) return 0;
    buf[0] = 0;
    size_t used = 0;
    pthread_mutex_lock(&L.lock);
    while (L.read < L.written) {
        const char *line = L.lines[L.read % LOG_LINES];
        size_t n = strlen(line);
        if (used + n + 2 > (size_t)len) break;  // the rest waits for the next call
        memcpy(buf + used, line, n); used += n; buf[used++] = '\n'; buf[used] = 0;
        L.read++;
    }
    pthread_mutex_unlock(&L.lock);
    return (int)used;
}

static __thread int t_status;   // what this connection answered (negative: the client hung up mid-answer)
static __thread size_t t_bytes;
static __thread char t_err[96];  // r9: why a request failed, on its log line (the 500s of build-138 said nothing)

int kr_remux_kind(const char *url) {
    if (!url) return KR_UNKNOWN;
    const char *end = url + strcspn(url, "?#");
    const char *dot = NULL;
    for (const char *p = url; p < end; p++) { if (*p == '.') dot = p; else if (*p == '/') dot = NULL; }
    if (!dot) return KR_UNKNOWN;
    char ext[8] = "";
    size_t n = (size_t)(end - dot - 1);
    if (n == 0 || n >= sizeof ext) return KR_UNKNOWN;
    for (size_t i = 0; i < n; i++) ext[i] = (char)tolower((unsigned char)dot[1 + i]);
    static const char *remux[] = { "mkv", "mk3d", "avi", "webm", "ts", "m2ts", "mts", NULL };
    static const char *direct[] = { "mp4", "m4v", "mov", "m3u8", NULL };
    for (int i = 0; remux[i]; i++) if (!strcmp(ext, remux[i])) return KR_REMUX;
    for (int i = 0; direct[i]; i++) if (!strcmp(ext, direct[i])) return KR_DIRECT;
    return KR_UNKNOWN;
}

int kr_remux_state(void) { return atomic_load(&S.state); }
const char *kr_remux_message(void) { return S.message; }
const char *kr_remux_video_codec(void) { return S.vcodec; }
int kr_remux_served(int video) { return atomic_load(video ? &S.served_video : &S.served_audio); }
int kr_remux_served_external(int video) { return atomic_load(video ? &S.served_ext_video : &S.served_ext_audio); }
int kr_remux_compat(void) { return atomic_load(&S.state) == KR_READY ? S.compat : 0; }
int kr_remux_port(void) { return atomic_load(&S.state) == KR_READY ? S.port : 0; }

// ── HTTP ───────────────────────────────────────────────────────────────────────
static int send_all(int fd, const void *p, size_t n) {
    const char *c = p;
    while (n) {
        ssize_t w = send(fd, c, n, MSG_NOSIGNAL);
        if (w < 0 && errno == EINTR) continue;
        if (w <= 0) return -1;
        c += w; n -= (size_t)w;
    }
    return 0;
}

static void respond(int fd, int head, const char *range, const char *type, const uint8_t *body, size_t len) {
    char h[512];
    size_t from = 0, to = len ? len - 1 : 0;
    int partial = 0;
    unsigned long long a = 0, b = 0;
    if (range && len) {
        int got = sscanf(range, "bytes=%llu-%llu", &a, &b);
        if (got >= 1 && a < len) { from = (size_t)a; if (got == 2 && b < len && b >= a) to = (size_t)b; partial = 1; }
        else if (got >= 1) {
            int n = snprintf(h, sizeof h, "HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */%zu\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", len);
            send_all(fd, h, (size_t)n); t_status = 416; return;
        }
    }
    size_t n_body = len ? to - from + 1 : 0;
    int n = partial
        ? snprintf(h, sizeof h, "HTTP/1.1 206 Partial Content\r\nContent-Type: %s\r\nContent-Length: %zu\r\nContent-Range: bytes %zu-%zu/%zu\r\nAccept-Ranges: bytes\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n", type, n_body, from, to, len)
        : snprintf(h, sizeof h, "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %zu\r\nAccept-Ranges: bytes\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n", type, n_body);
    t_status = partial ? 206 : 200;
    if (send_all(fd, h, (size_t)n) != 0) { t_status = -t_status; return; }
    if (!head && n_body) { if (send_all(fd, body + from, n_body) == 0) t_bytes = n_body; else t_status = -t_status; }
}

static void fail(int fd, int code, const char *why) {
    char h[256];
    int n = snprintf(h, sizeof h, "HTTP/1.1 %d %s\r\nContent-Length: 0\r\nConnection: close\r\n\r\n", code, why);
    send_all(fd, h, (size_t)n);
    t_status = code;
}

static int ends_with(const char *s, const char *tail) {
    size_t a = strlen(s), b = strlen(tail);
    return a >= b && !strcmp(s + a - b, tail);
}

static bridge *find_bridge(int index) {
    for (int i = 0; i < S.nbridges; i++) if (S.bridges[i].index == index) return &S.bridges[i];
    return NULL;
}

static int track_route(int index) { return index >= 0 && index < MAX_TRACKS ? S.routes[index] : KR_AUDIO_NONE; }

// r8: the connections and the converter that teardown aborts are published under src_lock (a leaf lock), so a stop
// never misses one that a request or a background job is opening at that moment: it is aborted as it is published.
static pthread_mutex_t src_lock = PTHREAD_MUTEX_INITIALIZER;

static void publish_source(kr_source **slot, kr_source *s) {
    pthread_mutex_lock(&src_lock);
    *slot = s;
    if (s && atomic_load(&S.stopping)) kr_source_abort(s);
    pthread_mutex_unlock(&src_lock);
}

// Opens the bridge for an audio track the first time AVPlayer asks for it (a second connection to the source).
static kr_audio *bridge_audio(bridge *b, char *err, int errlen) {
    if (b->audio) return b->audio;
    if (atomic_load(&S.stopping)) { snprintf(err, (size_t)errlen, "stopping"); return NULL; }
    kr_source *src = kr_source_open(S.url, 30, err, errlen);
    if (!src) return NULL;
    publish_source(&b->src, src);
    b->audio = kr_audio_open(kr_source_gm(src), b->index, err, errlen);
    if (!b->audio) { publish_source(&b->src, NULL); kr_source_close(src); }
    return b->audio;
}

// r7: the converter for the session's video, opened the first time the receiver asks for a video part (vlock held).
static kr_video *session_video(char *err, int errlen) {
    if (S.video) return S.video;
    if (atomic_load(&S.stopping)) { snprintf(err, (size_t)errlen, "stopping"); return NULL; }
    kr_source *src = kr_source_open(S.url, 30, err, errlen);
    if (!src) return NULL;
    publish_source(&S.vsrc, src);
    kr_video *v = kr_video_open(kr_source_gm(src), S.vindex, err, errlen);
    if (!v) { publish_source(&S.vsrc, NULL); kr_source_close(src); return NULL; }
    if (S.burn_index >= 0 || S.burn_file[0]) {  // r10: a subtitle that cannot be read leaves the picture as it is
        char e[128] = "";
        if (kr_video_burn(v, S.burn_index, S.burn_file, e, sizeof e) < 0) log_line("error: subtitles not burned in: %s", e);
        else if (S.burn_index >= 0)  // r11: a source stream's events are read with the picture, segment by segment
            log_line("compat: burning subtitles in (source stream %d: events load as each segment is converted)", S.burn_index);
        else log_line("compat: burning subtitles in (external file, %d events loaded)", kr_video_burn_events(v));
    }
    pthread_mutex_lock(&src_lock);
    S.video = v;
    if (atomic_load(&S.stopping)) kr_video_abort(v);
    pthread_mutex_unlock(&src_lock);
    log_line("compat: converting video stream %d to H.264 %dx%d with %s (%s decoding)", S.vindex, kr_video_width(S.video),
             kr_video_height(S.video), kr_video_encoder(), kr_video_hw_decode(S.video) ? "VideoToolbox" : "software");
    return S.video;
}

// r8: the audio-copy and subtitle demuxer: the same file opened a second time (its own connection) with the video
// demuxer's plan, so audio is made while a video segment is (agm_lock held). NULL when it cannot open: the caller then
// uses the video's demuxer under gm_lock (as before r8).
static gm_stream *audio_demuxer(void) {
    if (S.agm || S.agm_failed || atomic_load(&S.stopping)) return S.agm;
    char err[256] = "";
    publish_source(&S.asrc, kr_source_open(S.url, 30, err, sizeof err));
    if (S.asrc) S.agm = gm_stream_open(kr_source_gm(S.asrc), SEG_SECONDS, err, sizeof err);
    if (S.agm && gm_stream_adopt_plan(S.agm, S.gm) != 0) { gm_stream_close(S.agm); S.agm = NULL; snprintf(err, sizeof err, "different streams"); }
    if (S.agm && atomic_load(&S.stopping)) { gm_stream_close(S.agm); S.agm = NULL; }
    if (!S.agm) {
        kr_source *gone = S.asrc;
        publish_source(&S.asrc, NULL);
        kr_source_close(gone); S.agm_failed = 1;
        if (!atomic_load(&S.stopping)) log_line("audio: no second connection (%s): audio waits for video", err);
    }
    return S.agm;
}

// r11: the subtitle demuxer (sgm_lock held): a third connection, never shared with audio or video. NULL when it cannot
// open (the request then answers an empty cue file: subtitles never wait on, or hold, a media lane).
static gm_stream *subs_demuxer(void) {
    if (S.sgm || S.sgm_failed || atomic_load(&S.stopping)) return S.sgm;
    char err[256] = "";
    publish_source(&S.ssrc, kr_source_open(S.url, 8, err, sizeof err));
    if (S.ssrc) S.sgm = gm_stream_open(kr_source_gm(S.ssrc), SEG_SECONDS, err, sizeof err);
    if (S.sgm && gm_stream_adopt_plan(S.sgm, S.gm) != 0) { gm_stream_close(S.sgm); S.sgm = NULL; snprintf(err, sizeof err, "different streams"); }
    if (S.sgm && atomic_load(&S.stopping)) { gm_stream_close(S.sgm); S.sgm = NULL; }
    if (!S.sgm) {
        kr_source *gone = S.ssrc;
        publish_source(&S.ssrc, NULL);
        kr_source_close(gone); S.sgm_failed = 1;
        if (!atomic_load(&S.stopping)) log_line("subs: no subtitle connection (%s): empty cue files", err);
    }
    return S.sgm;
}

// r11: drops the SUBTITLES group from a master (the subtitles are burned into that client's picture: a TV asking for
// WebVTT it ignores only adds load). In place.
static void strip_subtitles(char *m) {
    if (!m) return;
    char *p;
    while ((p = strstr(m, "#EXT-X-MEDIA:TYPE=SUBTITLES"))) {
        char *e = strchr(p, '\n'); e = e ? e + 1 : p + strlen(p);
        memmove(p, e, strlen(e) + 1);
    }
    static const char attr[] = ",SUBTITLES=\"subs\"";
    while ((p = strstr(m, attr))) memmove(p, p + sizeof attr - 1, strlen(p + sizeof attr - 1) + 1);
}

// ── r8: production lanes ───────────────────────────────────────────────────────
// Each rendition is made under its lane's lock: the copied video on the session demuxer (gm_lock), the converted
// video on the converter's (vlock), copied audio and subtitles on the second demuxer (agm_lock), each AAC bridge on
// its own (bridge lock). Different lanes run at the same time.
static pthread_mutex_t *lane(int rend) {
    if (rend == R_VCOPY) return &S.gm_lock;
    if (rend == R_VCOMPAT) return &S.vlock;
    int idx = rend - R_AUDIO, route = track_route(idx);
    if (route == KR_AUDIO_COPY) return &S.agm_lock;
    if (route == KR_AUDIO_AAC) { bridge *b = find_bridge(idx); return b ? &b->lock : NULL; }
    return NULL;
}

// r9: the converted segment being made right now (any thread), -1 when none.
static atomic_int vc_seg = -1;

// The whole unit (ftyp+moov+moof+mdat) of segment seg of a rendition (its lane's lock held).
static int produce_unit(int rend, int seg, gm_buf *out, char *err, int errlen) {
    int split = 0, r = -1;
    if (atomic_load(&S.stopping)) { snprintf(err, (size_t)errlen, "stopping"); return -1; }
    if (rend == R_VCOPY) {
        int v = gm_stream_selected_video(S.gm);
        if (v < 0) { snprintf(err, (size_t)errlen, "no video track"); return -1; }
        return gm_stream_track_unit(S.gm, v, seg, out, &split, err, errlen);
    }
    if (rend == R_VCOMPAT) {
        kr_video *v = session_video(err, errlen);
        if (!v) return -1;
        atomic_store(&vc_seg, seg);
        double t0 = now_ms();
        r = kr_video_unit(v, S.gm, seg, out, err, errlen);
        atomic_store(&vc_seg, -1);
        if (r == 0) {  // r11: the conversion path and speed per segment (realtime = SEG_SECONDS per segment)
            double ms = now_ms() - t0, pct = ms / (SEG_SECONDS * 10.0);
            if (atomic_fetch_add(&S.vlogged, 1) < 3 || pct > 70)
                log_line("compat: segment %d converted in %.0f ms (%.0f%% of realtime) via %s, %d subtitle events, %ld frames drawn", seg,
                         ms, pct, kr_video_path(v), kr_video_burn_events(v), kr_video_burn_drawn(v));
        }
        return r;
    }
    int idx = rend - R_AUDIO, route = track_route(idx);
    if (route == KR_AUDIO_COPY) {
        gm_stream *g = audio_demuxer();
        if (g) return gm_stream_track_unit(g, idx, seg, out, &split, err, errlen);
        pthread_mutex_lock(&S.gm_lock);  // lock order: agm_lock, then gm_lock (never the other way)
        r = gm_stream_track_unit(S.gm, idx, seg, out, &split, err, errlen);
        pthread_mutex_unlock(&S.gm_lock);
        return r;
    }
    if (route == KR_AUDIO_AAC) {
        bridge *b = find_bridge(idx);
        kr_audio *a = b ? bridge_audio(b, err, errlen) : NULL;
        return a ? kr_audio_unit(a, S.gm, seg, out, err, errlen) : -1;
    }
    snprintf(err, (size_t)errlen, "no such track");
    return -1;
}

// ── r8: cache ──────────────────────────────────────────────────────────────────
// Inits are kept for the session (made once, from segment 0's unit). Media segments: the latest CACHE_SLOTS, at most
// CACHE_BYTES, least recently used out first; a segment made ahead and not yet asked for ("fresh") is never pushed
// out by another segment made ahead (that would throw away work), only by one a receiver asked for.
static struct {
    pthread_mutex_t lock;
    struct { int rend, seg, len, fresh; uint8_t *data; unsigned long used; } e[CACHE_SLOTS];
    int n;
    size_t bytes;
    unsigned long clock;
    uint8_t *init[NREND];
    int init_len[NREND];
} C = { .lock = PTHREAD_MUTEX_INITIALIZER };

static int cache_find(int rend, int seg) {
    for (int i = 0; i < C.n; i++) if (C.e[i].rend == rend && C.e[i].seg == seg) return i;
    return -1;
}

static int copy_out(gm_buf *out, const uint8_t *p, int len) {
    uint8_t *d = malloc(len > 0 ? (size_t)len : 1);
    if (!d) return 0;
    memcpy(d, p, (size_t)len);
    free(out->data); out->data = d; out->len = out->cap = len;
    return 1;
}

// A copy of the cached part (seg -1: the init) into out. 1 when cached.
static int cache_take(int rend, int seg, gm_buf *out) {
    int hit = 0;
    pthread_mutex_lock(&C.lock);
    if (seg < 0) hit = C.init[rend] && copy_out(out, C.init[rend], C.init_len[rend]);
    else {
        int i = cache_find(rend, seg);
        if (i >= 0 && copy_out(out, C.e[i].data, C.e[i].len)) { hit = 1; C.e[i].used = ++C.clock; C.e[i].fresh = 0; }
    }
    pthread_mutex_unlock(&C.lock);
    return hit;
}

static int cache_has(int rend, int seg) {
    pthread_mutex_lock(&C.lock);
    int has = seg < 0 ? C.init[rend] != NULL : cache_find(rend, seg) >= 0;
    pthread_mutex_unlock(&C.lock);
    return has;
}

static void cache_drop(int i) {
    C.bytes -= (size_t)C.e[i].len;
    free(C.e[i].data);
    C.e[i] = C.e[--C.n];
}

// Stores a copy. ahead: made in the background (kept "fresh" until asked for). 1 when stored.
static int cache_put(int rend, int seg, const uint8_t *p, int len, int ahead) {
    if (len <= 0) return 0;
    int stored = 0;
    pthread_mutex_lock(&C.lock);
    if (seg < 0) {
        if (!C.init[rend] && (C.init[rend] = malloc((size_t)len))) { memcpy(C.init[rend], p, (size_t)len); C.init_len[rend] = len; }
        stored = C.init[rend] != NULL;
    } else if (cache_find(rend, seg) >= 0) stored = 1;
    else if ((size_t)len <= CACHE_BYTES) {
        for (;;) {
            if (C.n < CACHE_SLOTS && C.bytes + (size_t)len <= CACHE_BYTES) break;
            int lru = -1;
            for (int i = 0; i < C.n; i++) if (lru < 0 || C.e[i].used < C.e[lru].used) lru = i;
            if (lru < 0 || (ahead && C.e[lru].fresh)) { lru = -1; break; }
            cache_drop(lru);
        }
        uint8_t *d = (C.n < CACHE_SLOTS && C.bytes + (size_t)len <= CACHE_BYTES) ? malloc((size_t)len) : NULL;
        if (d) {
            memcpy(d, p, (size_t)len);
            C.e[C.n].rend = rend; C.e[C.n].seg = seg; C.e[C.n].len = len; C.e[C.n].data = d;
            C.e[C.n].fresh = ahead; C.e[C.n].used = ++C.clock;
            C.n++; C.bytes += (size_t)len; stored = 1;
        }
    }
    pthread_mutex_unlock(&C.lock);
    return stored;
}

// Room for one more segment of this rendition made ahead (judged by the size of the ones already cached), next to
// the segments made ahead that nobody has asked for yet.
static int cache_room(int rend) {
    pthread_mutex_lock(&C.lock);
    size_t fresh = 0, size = 0;
    for (int i = 0; i < C.n; i++) {
        if (C.e[i].fresh) fresh += (size_t)C.e[i].len;
        if (C.e[i].rend == rend && (size_t)C.e[i].len > size) size = (size_t)C.e[i].len;
    }
    pthread_mutex_unlock(&C.lock);
    return fresh + size <= CACHE_BYTES;
}

static void cache_clear(void) {
    pthread_mutex_lock(&C.lock);
    while (C.n) cache_drop(C.n - 1);
    for (int i = 0; i < NREND; i++) { free(C.init[i]); C.init[i] = NULL; C.init_len[i] = 0; }
    C.bytes = 0;
    pthread_mutex_unlock(&C.lock);
}

// Makes segment seg's unit (lane lock held) and caches its parts: the init from segment 0, the media segment always.
// out (optional) gets the init (want_init) or the media segment.
static int make_part(int rend, int seg, int ahead, int want_init, gm_buf *out, char *err, int errlen) {
    gm_buf u = {0};
    int r = produce_unit(rend, seg, &u, err, errlen);
    if (r == 0) {
        int m = kr_first_moof(u.data, u.len);
        if (m <= 0 || m >= u.len) { snprintf(err, (size_t)errlen, "bad segment split"); r = -1; }
        else {
            if (seg == 0) cache_put(rend, -1, u.data, m, 0);
            cache_put(rend, seg, u.data + m, u.len - m, ahead);
            if (out && !(want_init ? copy_out(out, u.data, m) : copy_out(out, u.data + m, u.len - m))) {
                snprintf(err, (size_t)errlen, "out of memory"); r = -1;
            }
        }
    }
    free(u.data);
    return r;
}

// ── r8: segments made ahead ────────────────────────────────────────────────────
// After a receiver takes segment N of a rendition, N+1 and N+2 are made in the background (PF_WORKERS threads, each
// job under its lane's lock, so a video and an audio segment are made at the same time). A request for a segment far
// from the queued ones (a seek) drops them and cancels a conversion made for the old place.
static struct {
    pthread_mutex_t lock;
    pthread_cond_t cond;
    struct { int rend, seg; } q[PF_QUEUE];
    int n;
    int busy_rend[PF_WORKERS], busy_seg[PF_WORKERS];
    pthread_t th[PF_WORKERS];
    int started;
} P = { .lock = PTHREAD_MUTEX_INITIALIZER, .cond = PTHREAD_COND_INITIALIZER };

static atomic_int pf_on = 1;  // kr_remux_set_prefetch (tests)
static int near(int rend, int seg, int at) { return seg >= at && seg <= at + PF_DEPTH(rend); }

// Queues (rend, seg) unless it is cached, queued or being made (P.lock held).
static void push_locked(int rend, int seg) {
    if (seg < 0 || !S.gm || seg >= gm_stream_segment_count(S.gm) || cache_has(rend, seg)) return;
    for (int i = 0; i < P.n; i++) if (P.q[i].rend == rend && P.q[i].seg == seg) return;
    for (int w = 0; w < PF_WORKERS; w++) if (P.busy_rend[w] == rend && P.busy_seg[w] == seg) return;
    if (P.n == PF_QUEUE) { memmove(P.q, P.q + 1, sizeof P.q[0] * (PF_QUEUE - 1)); P.n--; }  // the oldest goes
    P.q[P.n].rend = rend; P.q[P.n].seg = seg; P.n++;
}

static void prefetch_push(int rend, int seg) {
    pthread_mutex_lock(&P.lock);
    if (P.started && atomic_load(&pf_on)) { push_locked(rend, seg); pthread_cond_broadcast(&P.cond); }
    pthread_mutex_unlock(&P.lock);
}

// A receiver wants segment seg of rend now: jobs of that rendition for other places are dropped, and a conversion
// running for another place gives up (the request would otherwise wait for it).
static void prefetch_focus(int rend, int seg) {
    pthread_mutex_lock(&P.lock);
    for (int i = 0; i < P.n;) {
        if (P.q[i].rend == rend && !near(rend, P.q[i].seg, seg)) { P.q[i] = P.q[--P.n]; continue; }
        i++;
    }
    for (int w = 0; w < PF_WORKERS; w++)
        if (rend == R_VCOMPAT && P.busy_rend[w] == rend && !near(rend, P.busy_seg[w], seg)) {
            pthread_mutex_lock(&src_lock);
            if (S.video) kr_video_cancel(S.video);
            pthread_mutex_unlock(&src_lock);
        }
    pthread_mutex_unlock(&P.lock);
}

// After serving segment seg of rend: the next PF_DEPTH(rend) segments.
static void prefetch_after(int rend, int seg) {
    pthread_mutex_lock(&P.lock);
    if (P.started && atomic_load(&pf_on)) {
        for (int k = 1; k <= PF_DEPTH(rend); k++) push_locked(rend, seg + k);
        pthread_cond_broadcast(&P.cond);
    }
    pthread_mutex_unlock(&P.lock);
}

static void *prefetch_worker(void *arg) {
    int me = (int)(intptr_t)arg;
    pthread_mutex_lock(&P.lock);
    while (!atomic_load(&S.stopping)) {
        int pick = -1;
        pthread_mutex_t *l = NULL;
        for (int i = 0; i < P.n && pick < 0; i++) {  // the oldest job whose lane is free (no waiting on a busy lane)
            pthread_mutex_t *c = lane(P.q[i].rend);
            if (!c) { P.q[i] = P.q[--P.n]; i--; continue; }
            if (pthread_mutex_trylock(c) == 0) { pick = i; l = c; }
        }
        if (pick < 0) {
            if (P.n == 0) pthread_cond_wait(&P.cond, &P.lock);
            else {  // every queued job's lane is busy: look again shortly
                struct timespec t; clock_gettime(CLOCK_REALTIME, &t);
                t.tv_nsec += 20 * 1000000L; if (t.tv_nsec >= 1000000000L) { t.tv_sec++; t.tv_nsec -= 1000000000L; }
                pthread_cond_timedwait(&P.cond, &P.lock, &t);
            }
            continue;
        }
        int rend = P.q[pick].rend, seg = P.q[pick].seg;
        memmove(P.q + pick, P.q + pick + 1, sizeof P.q[0] * (size_t)(P.n - pick - 1)); P.n--;
        P.busy_rend[me] = rend; P.busy_seg[me] = seg;
        pthread_mutex_unlock(&P.lock);
        if (!atomic_load(&S.stopping) && !cache_has(rend, seg) && cache_room(rend)) {
            char err[256] = "";
            if (make_part(rend, seg, 1, 0, NULL, err, sizeof err) == 0) atomic_fetch_add(&S.prefetched, 1);
            else if (!atomic_load(&S.stopping) && strcmp(err, "cancelled"))
                log_line("prefetch: %s segment %d: %s", rend == R_VCOPY ? "video" : rend == R_VCOMPAT ? "converted video" : "audio", seg, err);
        }
        pthread_mutex_unlock(l);
        pthread_mutex_lock(&P.lock);
        P.busy_rend[me] = -1; P.busy_seg[me] = -1;
        pthread_cond_broadcast(&P.cond);
    }
    pthread_mutex_unlock(&P.lock);
    return NULL;
}

static void prefetch_start(void) {
    pthread_mutex_lock(&P.lock);
    P.n = 0;
    for (int w = 0; w < PF_WORKERS; w++) {
        P.busy_rend[w] = P.busy_seg[w] = -1;
        if (pthread_create(&P.th[w], NULL, prefetch_worker, (void *)(intptr_t)w) == 0) P.started |= 1 << w;
    }
    pthread_mutex_unlock(&P.lock);
}

// S.stopping is set and the sources aborted: the workers finish their job quickly and end.
static void prefetch_stop(void) {
    pthread_mutex_lock(&P.lock);
    int started = P.started;
    P.started = 0; P.n = 0;
    pthread_cond_broadcast(&P.cond);
    pthread_mutex_unlock(&P.lock);
    for (int w = 0; w < PF_WORKERS; w++) if (started & (1 << w)) pthread_join(P.th[w], NULL);
}

// A media segment (seg >= 0) or init (seg -1) for a request: the cache, else made now (waiting for the lane: a
// background job making the same segment finishes first and the request takes its result).
static int get_part(int rend, int seg, gm_buf *out, char *err, int errlen) {
    if (seg < -1 || seg >= gm_stream_segment_count(S.gm)) { snprintf(err, (size_t)errlen, "bad segment index"); return -1; }
    if (cache_take(rend, seg, out)) return 0;
    pthread_mutex_t *l = lane(rend);
    if (!l) { snprintf(err, (size_t)errlen, "no such track"); return -1; }
    prefetch_focus(rend, seg < 0 ? 0 : seg);
    // r9: a conversion far from this request (a request the TV gave up on after a seek, build-138: seg16 waited
    // 3-8 s) gives up now instead of finishing first.
    int busy = atomic_load(&vc_seg), at = seg < 0 ? 0 : seg;
    if (rend == R_VCOMPAT && busy >= 0 && (busy < at - 1 || busy > at + PF_DEPTH_VIDEO)) {
        pthread_mutex_lock(&src_lock);
        if (S.video) kr_video_cancel(S.video);
        pthread_mutex_unlock(&src_lock);
    }
    pthread_mutex_lock(l);
    int r = cache_take(rend, seg, out) ? 0 : make_part(rend, seg < 0 ? 0 : seg, 0, seg < 0, out, err, errlen);
    pthread_mutex_unlock(l);
    return r;
}

// "BANDWIDTH=...,CODECS=..." of a master playlist.
static void variant_line(const char *master, char *out, size_t len) {
    const char *v = master ? strstr(master, "#EXT-X-STREAM-INF:") : NULL;
    snprintf(out, len, "%.*s", v ? (int)strcspn(v + 18, "\n") : 0, v ? v + 18 : "");
}

int kr_remux_third_party_receiver(const char *ua) {
    // Third-party AirPlay 2 receivers (TVs: TCL/Roku, Samsung, LG, Vizio...) fetch with "AirPlay/<v> (App/<v>)
    // MFi_AirPlay_Device (MFiModelGroup/...)"; Apple's players say AppleCoreMedia (iPhone, iPad, Apple TV) and keep the copy.
    if (!ua) return 0;
    static const char tag[] = "mfi_airplay_device";
    for (const char *p = ua; *p; p++) if (!strncasecmp(p, tag, sizeof tag - 1)) return 1;
    return 0;
}

// The phone's (or iPad's) own player: "AppleCoreMedia/1.0.0.24A446 (iPhone; U; CPU OS 27_0_1 like Mac OS X; en_us)".
// An Apple TV says "(Apple TV; ...)", a TV's AirPlay "MFi_AirPlay_Device": external receivers.
static int phone_player(const char *ua) {
    return ua && strstr(ua, "AppleCoreMedia") && (strstr(ua, "(iPhone") || strstr(ua, "(iPad") || strstr(ua, "(iPod"));
}

static void serve(int fd, const char *method, const char *path, const char *range, const char *agent) {
    int head = !strcmp(method, "HEAD");
    char err[256] = "";
    gm_buf buf = {0};
    int idx = -1, seg = -1, r = -1, rend = -1;
    char *text = NULL;
    const char *m3u8 = "application/vnd.apple.mpegurl";
    // r8: the converted picture for a third-party receiver while others get the copy (same grid: the same plan).
    int third = S.compat_ok && kr_remux_third_party_receiver(agent);
    int cvideo = !strncmp(path, "/cvideo/", 8);
    if (cvideo && !S.compat && !S.compat_ok) { fail(fd, 404, "Not Found"); return; }
    if (!strcmp(path, "/master.m3u8")) {
        const char *m = third ? S.master_compat : S.master_copy;
        if (third && atomic_fetch_add(&S.compat_clients, 1) == 0) {
            char v[256]; variant_line(m, v, sizeof v);
            log_line("compat: %.80s gets the picture as H.264: %.150s", agent, v);
        }
        if (m) text = strdup(m);
        // r9: a TV that gets the converted picture asks for its init and first segment next: start converting now,
        // while it reads the playlists (build-138: the first init/seg0 took ~4 s and the TV's player gave up).
        if (third || S.compat) prefetch_push(R_VCOMPAT, 0);
    } else if (!strcmp(path, "/video/index.m3u8") || !strcmp(path, "/cvideo/index.m3u8")) {
        char prefix[96]; snprintf(prefix, sizeof prefix, "%s/%s", S.base, cvideo ? "cvideo" : "video");
        text = kr_hls_media(S.gm, prefix, "m4s", 1);  // the plan only (fixed after open): no lock
    } else if (ends_with(path, "/index.m3u8") && (sscanf(path, "/audio/%d/", &idx) == 1 || sscanf(path, "/subs/%d/", &idx) == 1)) {
        int subs = path[1] == 's';
        char prefix[96]; snprintf(prefix, sizeof prefix, "%s/%s/%d", S.base, subs ? "subs" : "audio", idx);
        text = kr_hls_media(S.gm, prefix, subs ? "vtt" : "m4s", !subs);
    }
    if (text) { respond(fd, head, NULL, m3u8, (uint8_t *)text, strlen(text)); free(text); return; }

    const char *vpart = cvideo ? path + 7 : !strncmp(path, "/video/", 7) ? path + 6 : NULL;  // "/init.mp4", "/seg3.m4s"
    if (vpart && (!strcmp(vpart, "/init.mp4") || sscanf(vpart, "/seg%d.m4s", &seg) == 1)) {
        rend = (S.compat || cvideo || third) ? R_VCOMPAT : R_VCOPY;
        r = get_part(rend, seg, &buf, err, sizeof err);
    } else if (sscanf(path, "/subs/%d/seg%d.vtt", &idx, &seg) == 2) {
        // r11: on the subtitle demuxer only (its own connection and lock); busy or unavailable: an empty cue file now
        // (r10 held the audio lane for 5-13 s per cue file). A client whose picture has them burned in is not offered them.
        static const char empty[] = "WEBVTT\n\n";
        int burned = (S.burn_index >= 0 || S.burn_file[0]) && (S.compat || cvideo || third);
        int got = 0;
        if (!burned) for (int k = 0; k < 15 && !atomic_load(&S.stopping); k++) {  // up to ~1.5 s for a cue file in progress
            if (pthread_mutex_trylock(&S.sgm_lock) == 0) { got = 1; break; }
            usleep(100000);
        }
        r = -1;
        if (got) {
            gm_stream *g = subs_demuxer();
            if (g) r = gm_stream_subtitle_segment(g, idx, seg, &buf, err, sizeof err);
            pthread_mutex_unlock(&S.sgm_lock);
        }
        if (r == 0) { respond(fd, head, range, "text/vtt", buf.data, (size_t)buf.len); free(buf.data); return; }
        free(buf.data);
        if (got && !burned) log_line("subs: cue file %d of stream %d: %s (empty)", seg, idx, *err ? err : "unavailable");
        respond(fd, head, range, "text/vtt", (const uint8_t *)empty, sizeof empty - 1);
        return;
    } else if (sscanf(path, "/audio/%d/", &idx) == 1) {
        int init = strstr(path, "/init.mp4") != NULL;
        if (!init && sscanf(path, "/audio/%*d/seg%d.m4s", &seg) != 1) { fail(fd, 404, "Not Found"); return; }
        if (!track_route(idx)) { fail(fd, 404, "Not Found"); return; }
        rend = R_AUDIO + idx;
        r = get_part(rend, init ? -1 : seg, &buf, err, sizeof err);
    } else { fail(fd, 404, "Not Found"); return; }

    if (r == 0) {
        respond(fd, head, range, "video/mp4", buf.data, (size_t)buf.len);
        if (seg >= 0 && t_status > 0) {
            int audio = path[1] == 'a';
            atomic_fetch_add(audio ? &S.served_audio : &S.served_video, 1);
            if (!phone_player(agent)) atomic_fetch_add(audio ? &S.served_ext_audio : &S.served_ext_video, 1);
        }
        if (rend >= 0 && !head) prefetch_after(rend, seg < 0 ? 0 : seg);
    }
    else {
        if (!atomic_load(&S.stopping)) {
            char m[300]; snprintf(m, sizeof m, "AirPlay conversion failed on %.60s: %s", path, *err ? err : "unknown error");
            set_message(m);
            fprintf(stderr, "kodi-airplay-remux: %s\n", m);
            log_line("error: %s", m);
        }
        snprintf(t_err, sizeof t_err, "%s", atomic_load(&S.stopping) ? "session stopped" : *err ? err : "unknown error");
        fail(fd, 500, "Remux Failed");
    }
    free(buf.data);
}

int kr_remux_compat_clients(void) { return atomic_load(&S.compat_clients); }
int kr_remux_prefetched(void) { return atomic_load(&S.prefetched); }

// The phone's Wi-Fi IPv4 address (en0 on iOS; the first up, non-loopback IPv4 elsewhere).
static int lan_address(char *out, size_t len) {
    struct ifaddrs *list = NULL, *best = NULL;
    if (getifaddrs(&list) != 0) return -1;
    for (struct ifaddrs *i = list; i; i = i->ifa_next) {
        if (!i->ifa_addr || i->ifa_addr->sa_family != AF_INET || !(i->ifa_flags & IFF_UP) || (i->ifa_flags & IFF_LOOPBACK)) continue;
        if (!strcmp(i->ifa_name, "en0")) { best = i; break; }
        if (!best) best = i;
    }
    int r = -1;
    if (best && inet_ntop(AF_INET, &((struct sockaddr_in *)best->ifa_addr)->sin_addr, out, (socklen_t)len)) r = 0;
    freeifaddrs(list);
    return r;
}

static void random_token(char *out, size_t len) {
    unsigned char b[16] = {0};
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd >= 0) { if (read(fd, b, sizeof b) != (ssize_t)sizeof b) memset(b, 0, sizeof b); close(fd); }
    for (size_t i = 0; i < sizeof b && 2 * i + 2 < len; i++) snprintf(out + 2 * i, 3, "%02x", b[i]);
}

static void *connection(void *arg) {
    int fd = (int)(intptr_t)arg;
    char req[8192]; size_t got = 0;
    while (got < sizeof req - 1) {
        ssize_t n = recv(fd, req + got, sizeof req - 1 - got, 0);
        if (n <= 0) break;
        got += (size_t)n; req[got] = 0;
        if (strstr(req, "\r\n\r\n")) break;
    }
    req[got] = 0;
    char method[8] = "", path[1024] = "";
    if (sscanf(req, "%7s %1023s", method, path) == 2 && (!strcmp(method, "GET") || !strcmp(method, "HEAD"))) {
        char range[128] = "", agent[160] = "", *h = req;
        while ((h = strstr(h, "\r\n")) != NULL) {
            h += 2;
            if (!strncasecmp(h, "Range:", 6)) sscanf(h + 6, " %127[^\r\n]", range);
            else if (!strncasecmp(h, "User-Agent:", 11)) sscanf(h + 11, " %159[^\r\n]", agent);
        }
        log_agent(agent);
        char *q = strchr(path, '?'); if (q) *q = 0;
        size_t tl = strlen(S.token);
        t_status = 0; t_bytes = 0; t_err[0] = 0;
        double t0 = now_ms();
        int ok = path[0] == '/' && !strncmp(path + 1, S.token, tl) && path[1 + tl] == '/';
        if (ok) serve(fd, method, path + 1 + tl, *range ? range : NULL, agent);
        else fail(fd, 404, "Not Found");
        // "GET /video/seg3.m4s 200 1834567 B 412 ms"
        log_line("%s %s%s%s %d %zu B %.0f ms%s%s", method, ok ? path + 1 + tl : "(no token)", *range ? " " : "", range,
                 t_status, t_bytes, now_ms() - t0, *t_err ? ": " : "", t_err);
    } else fail(fd, 405, "Method Not Allowed");
    close(fd);
    atomic_fetch_sub(&S.active, 1);
    return NULL;
}

static void *accept_loop(void *unused) {
    (void)unused;
    while (!atomic_load(&S.stopping)) {
        int fd = accept(S.listen_fd, NULL, NULL);
        if (fd < 0) { if (errno == EINTR) continue; break; }
        if (atomic_load(&S.stopping)) { close(fd); break; }
#ifdef SO_NOSIGPIPE
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof one);
#endif
        struct timeval tv = { 60, 0 };
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
        atomic_fetch_add(&S.active, 1);
        pthread_t t;
        pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
        if (pthread_create(&t, &at, connection, (void *)(intptr_t)fd) != 0) { close(fd); atomic_fetch_sub(&S.active, 1); }
        pthread_attr_destroy(&at);
    }
    return NULL;
}

// Binds 127.0.0.1 on a port the system picks; tries again a few times if that fails.
static int listen_on(int lan, int *port) {
    for (int attempt = 0; attempt < 5; attempt++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) continue;
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        struct sockaddr_in a = { 0 };
        a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(lan ? INADDR_ANY : INADDR_LOOPBACK); a.sin_port = 0;
        socklen_t len = sizeof a;
        if (bind(fd, (struct sockaddr *)&a, sizeof a) == 0 && listen(fd, 32) == 0 &&
            getsockname(fd, (struct sockaddr *)&a, &len) == 0) { *port = ntohs(a.sin_port); return fd; }
        close(fd);
    }
    return -1;
}

static void teardown_locked(void) {
    pthread_mutex_lock(&src_lock);  // r8: what is being opened right now is aborted when it is published
    atomic_store(&S.stopping, 1);
    if (S.src) kr_source_abort(S.src);
    if (S.asrc) kr_source_abort(S.asrc);
    if (S.ssrc) kr_source_abort(S.ssrc);
    for (int i = 0; i < S.nbridges; i++) if (S.bridges[i].src) kr_source_abort(S.bridges[i].src);
    // r7: a conversion in progress stops at its next packet (no transcoding once the server stops).
    if (S.video) kr_video_abort(S.video);
    if (S.vsrc) kr_source_abort(S.vsrc);
    pthread_mutex_unlock(&src_lock);
    if (S.listen_fd >= 0) {
        shutdown(S.listen_fd, SHUT_RDWR); close(S.listen_fd); S.listen_fd = -1;
        pthread_join(S.accept_thread, NULL);
    }
    prefetch_stop();  // r8: background producers end (their reads fail now) before anything is freed
    for (int i = 0; i < 400 && atomic_load(&S.active) > 0; i++) usleep(10000);  // up to 4 s for open requests
    pthread_mutex_lock(&S.agm_lock);
    gm_stream_close(S.agm); S.agm = NULL;
    kr_source *asrc = S.asrc;
    publish_source(&S.asrc, NULL);
    kr_source_close(asrc);
    S.agm_failed = 0;
    pthread_mutex_unlock(&S.agm_lock);
    pthread_mutex_lock(&S.sgm_lock);
    gm_stream_close(S.sgm); S.sgm = NULL;
    kr_source *ssrc = S.ssrc;
    publish_source(&S.ssrc, NULL);
    kr_source_close(ssrc);
    S.sgm_failed = 0;
    pthread_mutex_unlock(&S.sgm_lock);
    pthread_mutex_lock(&S.gm_lock);
    if (S.gm) { gm_stream_close(S.gm); S.gm = NULL; }
    if (S.src) { kr_source_close(S.src); S.src = NULL; }
    pthread_mutex_unlock(&S.gm_lock);
    for (int i = 0; i < S.nbridges; i++) {
        pthread_mutex_lock(&S.bridges[i].lock);
        kr_audio_close(S.bridges[i].audio); S.bridges[i].audio = NULL;
        kr_source *bsrc = S.bridges[i].src;
        publish_source(&S.bridges[i].src, NULL);
        kr_source_close(bsrc);
        pthread_mutex_unlock(&S.bridges[i].lock);
        pthread_mutex_destroy(&S.bridges[i].lock);
    }
    S.nbridges = 0; S.port = 0;
    pthread_mutex_lock(&S.vlock);  // a request still converting has finished or given up (abort above)
    pthread_mutex_lock(&src_lock);
    kr_video *video = S.video; kr_source *vsrc = S.vsrc;
    S.video = NULL; S.vsrc = NULL;
    pthread_mutex_unlock(&src_lock);
    kr_video_close(video);
    kr_source_close(vsrc);
    pthread_mutex_unlock(&S.vlock);
    S.compat = 0; S.vindex = -1; S.compat_ok = 0;
    atomic_store(&S.vlogged, 0);
    free(S.master_copy); S.master_copy = NULL;
    free(S.master_compat); S.master_compat = NULL;
    for (int i = 0; i < MAX_TRACKS; i++) S.routes[i] = KR_AUDIO_NONE;
    cache_clear();
}

void kr_remux_stop(void) {
    pthread_mutex_lock(&S.lock);
    teardown_locked();
    atomic_store(&S.state, KR_IDLE);
    set_message("");
    pthread_mutex_unlock(&S.lock);
}

static int is_direct_format(const char *name) {
    return name && (strstr(name, "mp4") || strstr(name, "mov") || !strcmp(name, "hls"));
}

int kr_remux_start(const char *url, int lan, int compat, char *out, int outlen) {
    pthread_mutex_lock(&S.lock);
    teardown_locked();
    atomic_store(&S.stopping, 0);
    atomic_store(&S.served_video, 0); atomic_store(&S.served_audio, 0); S.vcodec[0] = 0;
    atomic_store(&S.compat_clients, 0); atomic_store(&S.prefetched, 0);
    atomic_store(&S.served_ext_video, 0); atomic_store(&S.served_ext_audio, 0);
    atomic_store(&S.state, KR_STARTING);
    set_message("");
    if (out && outlen > 0) *out = 0;
    char err[256] = "";
    int result = KR_FAILED;
    snprintf(S.url, sizeof S.url, "%s", url ? url : "");
    S.src = kr_source_open(S.url, 30, err, sizeof err);
    pthread_mutex_lock(&L.lock); memset(L.agents, 0, sizeof L.agents); pthread_mutex_unlock(&L.lock);
    log_line("start: %.*s", (int)(strcspn(S.url, "?") < 200 ? strcspn(S.url, "?") : 200), S.url);  // no query (tokens)
    if (!S.src) { char m[300]; snprintf(m, sizeof m, "AirPlay: %s.", err); set_message(m); goto done; }
    {   // MP4/MOV bytes behind a URL without an extension (a Drive link): Apple's player takes the URL itself
        uint8_t pad[4096 + AVPROBE_PADDING_SIZE] = {0};
        int n = kr_source_read(S.src, 0, pad, 4096);
        AVProbeData pd = { "", pad, n > 0 ? n : 0, NULL };
        const AVInputFormat *fmt = n > 0 ? av_probe_input_format(&pd, 1) : NULL;
        if (fmt && is_direct_format(fmt->name)) { result = KR_NOT_NEEDED; goto done; }
    }
    S.gm = gm_stream_open(kr_source_gm(S.src), SEG_SECONDS, err, sizeof err);
    if (!S.gm) {
        char m[300];
        snprintf(m, sizeof m, "AirPlay cannot play this file: %s.", *err ? err : "the video is not H.264 or HEVC");
        set_message(m);
        goto done;
    }
    // Every audio track Apple cannot carry but we can decode gets a bridge (opened on first use).
    gm_track_info t;
    int playable_audio = 0, audio_tracks = 0;
    for (int i = 0; i < gm_stream_track_count(S.gm) && S.nbridges < MAX_TRACKS; i++) {
        if (gm_stream_track_info(S.gm, i, &t) != 0 || t.kind != GM_TRACK_AUDIO) continue;
        audio_tracks++;
        int route = kr_audio_route(&t);
        if (route) playable_audio++;
        if (t.src_index >= 0 && t.src_index < MAX_TRACKS) S.routes[t.src_index] = route;
        if (route == KR_AUDIO_AAC && t.src_index < MAX_TRACKS) {
            bridge *b = &S.bridges[S.nbridges++];
            memset(b, 0, sizeof *b); b->index = t.src_index; pthread_mutex_init(&b->lock, NULL);
        }
    }
    // r7: compat mode converts the picture. Asked for (the TV played sound only), or needed: the file's video is not
    // one AirPlay carries (VP9, MPEG-2...) but FFmpeg decodes it.
    S.vindex = kr_video_pick_stream(S.gm);
    if (!compat && gm_stream_selected_video(S.gm) < 0 && S.vindex >= 0 && kr_video_available()) {
        compat = 1;
        log_line("compat: the video is not H.264/HEVC, converting it");
    }
    if (compat) {
        if (S.vindex < 0) { set_message("AirPlay: this file has no video that can be converted."); goto done; }
        if (!kr_video_available()) { set_message("AirPlay: this build cannot convert video (no H.264 encoder)."); goto done; }
        S.compat = 1;
    }
    {   // r10: the subtitles to burn into the converted picture (Kodi's choice, else the file's default / forced)
        AVFormatContext *f = gm_stream_format_context(S.gm);
        pthread_mutex_lock(&SUBS.lock);
        int ord = SUBS.ordinal; char lang[16]; snprintf(lang, sizeof lang, "%s", SUBS.lang);
        S.burn_index = -1; S.burn_file[0] = 0;
        if (ord >= 0 && ord >= kr_subs_stream_count(f) && SUBS.file[0]) snprintf(S.burn_file, sizeof S.burn_file, "%s", SUBS.file);
        else if (ord == -2 && SUBS.file[0]) snprintf(S.burn_file, sizeof S.burn_file, "%s", SUBS.file);
        else S.burn_index = kr_subs_pick(f, ord, lang);
        pthread_mutex_unlock(&SUBS.lock);
        if (S.burn_index >= 0) log_line("subtitles: burning source stream %d into the converted picture", S.burn_index);
        else if (S.burn_file[0]) log_line("subtitles: burning an external file (%s) into the converted picture",
                                          strrchr(S.burn_file, '.') ? strrchr(S.burn_file, '.') : "?");
        else if (ord != -1) log_line("subtitles: none to burn in (Kodi's choice %d is not a text subtitle)", ord);
    }
    {   // r8: per receiver: a third-party AirPlay TV gets the converted picture when the source video is not H.264
        // r10: or when subtitles are to be burned in (such TVs ignore the WebVTT rendition): H.264 is converted too
        AVFormatContext *f = gm_stream_format_context(S.gm);
        int v = gm_stream_selected_video(S.gm);
        int burn = S.burn_index >= 0 || S.burn_file[0];
        S.compat_ok = !S.compat && v >= 0 && S.vindex >= 0 && f && (burn || f->streams[v]->codecpar->codec_id != AV_CODEC_ID_H264) &&
                      kr_video_available();
    }
    if (audio_tracks && !playable_audio) {
        set_message("AirPlay: this file's audio format cannot be converted, so it would play silent. Use Play on TV instead.");
        goto done;
    }
    char host[64] = "127.0.0.1";
    if (lan && lan_address(host, sizeof host) != 0) {
        set_message("AirPlay needs Wi-Fi: the TV fetches the video from the phone over the local network.");
        goto done;
    }
    S.listen_fd = listen_on(lan, &S.port);
    if (S.listen_fd < 0) { set_message("AirPlay: could not start the local streaming server."); goto done; }
    random_token(S.token, sizeof S.token);
    snprintf(S.base, sizeof S.base, "http://%s:%d/%s", host, S.port, S.token);
    if (pthread_create(&S.accept_thread, NULL, accept_loop, NULL) != 0) {
        close(S.listen_fd); S.listen_fd = -1;
        set_message("AirPlay: could not start the local streaming server."); goto done;
    }
    if (out && outlen > 0) snprintf(out, (size_t)outlen, "%s/master.m3u8", S.base);
    // r8: the playlists are fixed for the session: made once here, served without touching the demuxer.
    S.master_copy = kr_hls_master(S.gm, S.base, S.compat);
    if (S.compat_ok) S.master_compat = kr_hls_master_at(S.gm, S.base, 1, "cvideo");
    if (!S.master_copy || (S.compat_ok && !S.master_compat)) { set_message("AirPlay: out of memory."); goto done; }
    if (S.burn_index >= 0 || S.burn_file[0]) {  // r11: burned in: no WebVTT rendition for the converted picture
        strip_subtitles(S.master_compat);
        if (S.compat) strip_subtitles(S.master_copy);
    }
    {   // r6: the variant line the receiver judges the stream by (CODECS, RESOLUTION, VIDEO-RANGE), for the log
        char v[256];
        variant_line(S.master_copy, v, sizeof v);
        log_line("master: %.200s", v);
        if (S.compat) {  // the declared CODECS of the converted picture
            char *c = strstr(v, "CODECS=\"");
            snprintf(S.vcodec, sizeof S.vcodec, "%.*s", c ? (int)strcspn(c + 8, ",\"") : 0, c ? c + 8 : "");
        } else kr_hls_video_codec(S.gm, S.vcodec, sizeof S.vcodec);
        if (S.compat_ok) log_line("compat: third-party AirPlay receivers (MFi_AirPlay_Device) get the picture as H.264, others the %s copy", S.vcodec);
    }
    // r8: background producers, and the start of the default video and audio made before the receiver asks.
    prefetch_start();
    prefetch_push(S.compat ? R_VCOMPAT : R_VCOPY, 0);
    {
        int a = gm_stream_selected_audio(S.gm);
        gm_track_info t;
        for (int i = 0; a < 0 && i < gm_stream_track_count(S.gm); i++)
            if (gm_stream_track_info(S.gm, i, &t) == 0 && t.src_index < MAX_TRACKS && S.routes[t.src_index]) a = t.src_index;
        if (a >= 0 && a < MAX_TRACKS && S.routes[a]) prefetch_push(R_AUDIO + a, 0);
    }
    result = KR_READY;
done:
    if (result != KR_READY) { log_line("start result %d: %s", result, S.message); teardown_locked(); }
    atomic_store(&S.state, result);
    pthread_mutex_unlock(&S.lock);
    return result;
}
void kr_remux_set_prefetch(int on) { atomic_store(&pf_on, on != 0); }
