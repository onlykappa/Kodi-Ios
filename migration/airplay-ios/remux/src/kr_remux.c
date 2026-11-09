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
#include "kr_prepare.h"
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
#include <libavcodec/avcodec.h>
#include <libavutil/dovi_meta.h>
#include <libavutil/pixdesc.h>
#include <libavutil/bprint.h>
#include <libavutil/intreadwrite.h>
#include <math.h>

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
#define CACHE_BYTES (128u << 20) // also retains an older prepared movie's up-to-96-MiB random-access unit

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
    atomic_uint ticket;
    atomic_llong startup_deadline_ms;
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
    int prepared;
    int64_t prepared_size;
    char *prepared_master, *prepared_media;  // r38: HLS byte-range playlists over the prepared file (NULL: plain MP4)
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
    atomic_llong subtitle_deadline_ms;
    char burn_file[1024];      // external subtitle file when burn_index < 0, "" none
    char burn_language[16];
} S = { .lock = PTHREAD_MUTEX_INITIALIZER, .gm_lock = PTHREAD_MUTEX_INITIALIZER, .vlock = PTHREAD_MUTEX_INITIALIZER,
        .agm_lock = PTHREAD_MUTEX_INITIALIZER, .sgm_lock = PTHREAD_MUTEX_INITIALIZER, .listen_fd = -1, .vindex = -1, .burn_index = -1 };

// r10: the subtitle choice for the next kr_remux_start (Kodi's selection, from Python).
static struct { pthread_mutex_t lock; int ordinal; char file[1024]; char lang[16]; } SUBS = { PTHREAD_MUTEX_INITIALIZER, -2, "", "" };
// Registered sockets are shut down before a session is freed/reused, including clients which
// disconnected during a seek or connected without completing an HTTP request.
#define CONNECTION_LIMIT 64
static struct {pthread_mutex_t lock;int fd[CONNECTION_LIMIT];} CLIENTS={.lock=PTHREAD_MUTEX_INITIALIZER};
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
static atomic_uint request_ticket;
static pthread_mutex_t ticket_lock=PTHREAD_MUTEX_INITIALIZER;
static void abort_sources(void);

// r34: readable without draining the shared log or waiting for source I/O under S.lock.
static struct {
    pthread_mutex_t lock;
    double start_ms, listen_ms, first_tv_ms, player_ms, connect_ms;
    int expected, port, tv_requests, tv_media, tv_video;
    unsigned ticket;
    const char *phase;
    char host[64];
} N = { .lock = PTHREAD_MUTEX_INITIALIZER };

static double now_ms(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000.0 + t.tv_nsec / 1e6;
}

int kr_remux_network(char *buf, int len) {
    if (!buf || len <= 0) return 0;
    double now = now_ms();
    pthread_mutex_lock(&N.lock);
    snprintf(buf, (size_t)len, "{\"expected\":%d,\"host\":\"%s\",\"port\":%d,\"start_age_s\":%.3f,\"listen_age_s\":%.3f,\"tv_requests\":%d,\"tv_media\":%d,\"tv_video\":%d,\"first_tv_s\":%.3f,\"phase\":\"%s\",\"ticket\":%u,\"player_age_s\":%.3f,\"connect_age_s\":%.3f}",
             N.expected, N.host, N.port, N.start_ms ? (now-N.start_ms)/1000.0 : -1.0, N.listen_ms ? (now-N.listen_ms)/1000.0 : -1.0,
             N.tv_requests,N.tv_media,N.tv_video, N.first_tv_ms ? (N.first_tv_ms-N.start_ms)/1000.0 : -1.0,N.phase ? N.phase : "idle",N.ticket,
             N.player_ms ? (now-N.player_ms)/1000.0 : -1.0,N.connect_ms ? (now-N.connect_ms)/1000.0 : -1.0);
    pthread_mutex_unlock(&N.lock);
    return (int)strlen(buf);
}

static void network_begin_for(int lan,unsigned ticket) {
    pthread_mutex_lock(&N.lock);
    if(ticket==atomic_load(&request_ticket)) {
        N.start_ms=now_ms();N.listen_ms=N.first_tv_ms=N.player_ms=N.connect_ms=0;N.tv_requests=N.tv_media=N.tv_video=N.port=0;
        N.host[0]=0;N.expected=lan;N.ticket=ticket;N.phase="opening";
    }
    pthread_mutex_unlock(&N.lock);
}

void kr_remux_network_begin(int lan) { network_begin_for(lan,atomic_load(&request_ticket)); }

static void phase_for(unsigned ticket,const char *phase) {
    pthread_mutex_lock(&N.lock);
    if(N.ticket==ticket && ticket==atomic_load(&request_ticket)) N.phase=phase;
    pthread_mutex_unlock(&N.lock);
}

void kr_remux_player(unsigned ticket,int route_selected) {
    pthread_mutex_lock(&N.lock);
    if(N.ticket==ticket && ticket==atomic_load(&request_ticket) &&
       ((!N.expected && N.phase && !strcmp(N.phase,"opening")) ||
        (N.phase && (!strcmp(N.phase,"ready") || !strcmp(N.phase,"waiting_tv") ||
                     !strcmp(N.phase,"connecting") || !strcmp(N.phase,"playing"))))) {
        if(!N.player_ms)N.player_ms=now_ms();
        if(route_selected && !N.connect_ms)N.connect_ms=now_ms();
        N.phase=N.tv_video ? "playing" : (N.tv_requests || N.connect_ms) ? "connecting" : "waiting_tv";
    }
    pthread_mutex_unlock(&N.lock);
}

unsigned kr_remux_begin(int lan) {
    pthread_mutex_lock(&ticket_lock);
    unsigned ticket=atomic_fetch_add(&request_ticket,1)+1;
    abort_sources();network_begin_for(lan,ticket);
    pthread_mutex_unlock(&ticket_lock);
    return ticket;
}

void kr_remux_cancel(unsigned ticket) {
    pthread_mutex_lock(&ticket_lock);
    unsigned current=atomic_load(&request_ticket);
    if(!ticket || ticket==current) {
        atomic_fetch_add(&request_ticket,1);abort_sources();
        pthread_mutex_lock(&N.lock);
        if(N.ticket==current){N.phase="canceled";N.expected=0;}
        pthread_mutex_unlock(&N.lock);
    }
    pthread_mutex_unlock(&ticket_lock);
}

int kr_remux_external_peer(const char *peer, const char *host, const char *agent) {
    struct in_addr address;
    if (!peer || inet_pton(AF_INET,peer,&address)!=1 || !address.s_addr ||
        (ntohl(address.s_addr)>>24)==127 || (host && !strcmp(peer,host))) return 0;
    for (const char *p=agent;p && *p;p++)
        if(!strncasecmp(p,"iPhone",6) || !strncasecmp(p,"iPad",4)) return 0;
    return 1;
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

// r20: preparation (kr_prepare.c) writes its per-segment timing and route to the same log Kodi relays.
void kr_remux_note(const char *fmt, ...) {
    char line[LOG_WIDTH];
    va_list ap; va_start(ap, fmt); vsnprintf(line, sizeof line, fmt, ap); va_end(ap);
    log_line("%s", line);
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
static __thread int t_tv,t_media_marked;
static void media_sent(int video) {
    if(!t_tv || t_media_marked)return;
    t_media_marked=1;
    pthread_mutex_lock(&N.lock);
    if(N.ticket==atomic_load(&S.ticket) && N.ticket==atomic_load(&request_ticket)) {
        N.tv_media++;if(video)N.tv_video++;
        if(N.tv_video)N.phase="playing";
    }
    pthread_mutex_unlock(&N.lock);
}

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
    static const char *remux[] = { "mkv", "mk3d", "avi", "webm", "ts", "m2ts", "mts", "mp4", "m4v", "mov",
                                  "mpg", "mpeg", "vob", "wmv", "asf", "flv", "ogv", "rm", "rmvb", "wtv", "nut", NULL };
    static const char *direct[] = { "m3u8", NULL };
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
static kr_source *prepared_source; // published separately: PC.lock can be held during an upstream read

static void abort_sources(void) {
    pthread_mutex_lock(&src_lock);
    atomic_store(&S.stopping,1);
    if(S.src)kr_source_abort(S.src);
    if(S.asrc)kr_source_abort(S.asrc);
    if(S.ssrc)kr_source_abort(S.ssrc);
    if(S.vsrc)kr_source_abort(S.vsrc);
    if(prepared_source)kr_source_abort(prepared_source);
    for(int i=0;i<S.nbridges;i++)if(S.bridges[i].src)kr_source_abort(S.bridges[i].src);
    if(S.video)kr_video_abort(S.video);
    pthread_mutex_unlock(&src_lock);
}

static int source_interrupted(void *opaque) {
    unsigned ticket=(unsigned)(uintptr_t)opaque;
    long long deadline=atomic_load(&S.startup_deadline_ms);
    return ticket!=atomic_load(&request_ticket) || atomic_load(&S.stopping) || (deadline && now_ms()>=deadline);
}

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
    kr_source *src = kr_source_clone(S.src,30,source_interrupted,(void *)(uintptr_t)atomic_load(&S.ticket));
    if (!src) return NULL;
    publish_source(&b->src, src);
    b->audio = kr_audio_open(kr_source_gm(src), b->index, err, errlen);
    if (!b->audio) { publish_source(&b->src, NULL); kr_source_close(src); }
    return b->audio;
}

// r7: the converter for the session's video, opened the first time the receiver asks for a video part (vlock held).
static int video_read_interrupted(void *opaque) {
    return kr_video_interrupted(opaque) || source_interrupted((void *)(uintptr_t)atomic_load(&S.ticket));
}
static void video_init_ready(void *context,const uint8_t *data,int len);

static kr_video *session_video(char *err, int errlen) {
    if (S.video) return S.video;
    if (atomic_load(&S.stopping)) { snprintf(err, (size_t)errlen, "stopping"); return NULL; }
    kr_source *src = kr_source_clone(S.src,30,source_interrupted,(void *)(uintptr_t)atomic_load(&S.ticket));
    if (!src) return NULL;
    publish_source(&S.vsrc, src);
    kr_video *v = kr_video_open(kr_source_gm(src), S.vindex, err, errlen);
    if (!v) { publish_source(&S.vsrc, NULL); kr_source_close(src); return NULL; }
    kr_video_on_init(v,video_init_ready,NULL);
    if (S.burn_index >= 0 || S.burn_file[0]) {  // r10: a subtitle that cannot be read leaves the picture as it is
        char e[128] = "";
        kr_video_subtitle_language(v, S.burn_language);
        if (kr_video_burn(v, S.burn_index, S.burn_file, e, sizeof e) < 0) log_line("error: subtitles not burned in: %s", e);
        else if (S.burn_index >= 0)  // r11: a source stream's events are read with the picture, segment by segment
            log_line("compat: burning subtitles in (source stream %d: events load as each segment is converted)", S.burn_index);
        else log_line("compat: burning subtitles in (external file, %d events loaded)", kr_video_burn_events(v));
    }
    pthread_mutex_lock(&src_lock);
    kr_source_set_interrupt(src,video_read_interrupted,v);
    S.video = v;
    if (atomic_load(&S.stopping)) kr_video_abort(v);
    pthread_mutex_unlock(&src_lock);
    log_line("compat: converting video stream %d to H.264 %dx%d with %s (%s)", S.vindex, kr_video_width(S.video),
             kr_video_height(S.video), kr_video_encoder(), kr_video_hw_decode(S.video) ? "VideoToolbox requested" : "software decoding");
    return S.video;
}

// r8: the audio-copy and subtitle demuxer: the same file opened a second time (its own connection) with the video
// demuxer's plan, so audio is made while a video segment is (agm_lock held). NULL when it cannot open: the caller then
// uses the video's demuxer under gm_lock (as before r8).
static gm_stream *audio_demuxer(void) {
    if (S.agm || S.agm_failed || atomic_load(&S.stopping)) return S.agm;
    char err[256] = "";
    publish_source(&S.asrc, kr_source_clone(S.src,30,source_interrupted,(void *)(uintptr_t)atomic_load(&S.ticket)));
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
static int subtitle_interrupted(void *opaque) {
    long long end=atomic_load(&S.subtitle_deadline_ms);
    return source_interrupted(opaque) || (end && now_ms()>=end);
}
static gm_stream *subs_demuxer(void) {
    if (S.sgm || S.sgm_failed || atomic_load(&S.stopping)) return S.sgm;
    char err[256] = "";
    publish_source(&S.ssrc, kr_source_clone(S.src,2,subtitle_interrupted,(void *)(uintptr_t)atomic_load(&S.ticket)));
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
        double at=now_ms(),io=kr_source_io_ms(S.src);
        int result=gm_stream_track_unit(S.gm, v, seg, out, &split, err, errlen);
        if(now_ms()-at>1000)log_line("copy: video segment %d in %.0f ms, source I/O %.0f ms, result %d",seg,now_ms()-at,kr_source_io_ms(S.src)-io,result);
        return result;
    }
    if (rend == R_VCOMPAT) {
        double io0 = kr_source_io_ms(S.vsrc), t0 = now_ms();
        kr_video *v = session_video(err, errlen);
        if (!v) return -1;
        atomic_store(&vc_seg, seg);
        r = kr_video_unit(v, S.gm, seg, out, err, errlen);
        if(seg==0 && r<0 && r!=KR_VIDEO_CANCELLED && !atomic_load(&S.stopping) && strstr(err,"no video in this segment")) {
            // A canceled initial unit may leave no cached beginning, and some demuxers (FLV) cannot rewind
            // from a later segment to zero. Reopen once and use its buffered initial packets instead.
            pthread_mutex_lock(&src_lock);
            kr_source *old=S.vsrc;kr_source_set_interrupt(old,NULL,NULL);S.video=NULL;S.vsrc=NULL;
            pthread_mutex_unlock(&src_lock);kr_video_close(v);kr_source_close(old);
            log_line("seek: reopen decoder for the beginning after an empty rewind");
            v=session_video(err,errlen);io0=0;
            r=v?kr_video_unit(v,S.gm,seg,out,err,errlen):-1;
        }
        atomic_store(&vc_seg, -1);
        if(r==KR_VIDEO_CANCELLED) {
            // FFmpeg's parser can retain a half-read block after an interrupted HTTP wait. Retire this
            // speculative decoder/source; the next foreground request gets a clean independent instance.
            pthread_mutex_lock(&src_lock);
            kr_source *interrupted=S.vsrc;
            kr_source_set_interrupt(interrupted,NULL,NULL);
            S.video=NULL;S.vsrc=NULL;
            pthread_mutex_unlock(&src_lock);
            kr_video_close(v);kr_source_close(interrupted);
            log_line("seek: retired canceled background decoder/source");
            return r;
        }
        if (r == 0) {  // r11: the conversion path and speed per segment (realtime = SEG_SECONDS per segment)
            double ms = now_ms() - t0, pct = ms / (SEG_SECONDS * 10.0);
            if (atomic_fetch_add(&S.vlogged, 1) < 3 || pct > 70)
                log_line("compat: segment %d converted in %.0f ms (%.0f%% of realtime) via %s, source I/O %.0f ms, %d subtitle events, %ld frames drawn, subtitle preroll through %.3f s", seg,
                         ms, pct, kr_video_path(v), kr_source_io_ms(S.vsrc) - io0, kr_video_burn_events(v), kr_video_burn_drawn(v),kr_video_subtitle_scan_end(v));
        } else if (r != KR_VIDEO_CANCELLED) {
            log_line("compat: segment %d %s after %.0f ms, source I/O %.0f ms", seg,
                     atomic_load(&S.stopping) ? "stopped" : "failed", now_ms() - t0, kr_source_io_ms(S.vsrc) - io0);
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

static void video_init_ready(void *context,const uint8_t *data,int len) {
    (void)context;
    if(!atomic_load(&S.stopping))cache_put(R_VCOMPAT,-1,data,len,0);
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
// A foreground request owns priority over speculative work on its rendition.
static atomic_int demand[NREND];
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
            log_line("seek: cancel background converted segment %d for request %d", P.busy_seg[w], seg);
        }
    pthread_mutex_unlock(&P.lock);
}

// After serving segment seg of rend: the next PF_DEPTH(rend) segments.
static void prefetch_after(int rend, int seg) {
    pthread_mutex_lock(&P.lock);
    if (P.started && atomic_load(&pf_on)) {
        int depth=PF_DEPTH(rend);
        if(S.gm && gm_stream_segment_duration(S.gm,seg)>SEG_SECONDS*2)depth=1;
        for (int k = 1; k <= depth; k++) push_locked(rend, seg + k);
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
            if (atomic_load(&demand[P.q[i].rend])) continue;
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
        if (!atomic_load(&S.stopping) && !atomic_load(&demand[rend]) && !cache_has(rend, seg) && cache_room(rend)) {
            char err[256] = "";
            int r = make_part(rend, seg, 1, 0, NULL, err, sizeof err);
            if (r == 0) atomic_fetch_add(&S.prefetched, 1);
            else if (!atomic_load(&S.stopping) && !(rend == R_VCOMPAT && r == KR_VIDEO_CANCELLED))
                log_line("prefetch: %s segment %d: %s", rend == R_VCOPY ? "video" : rend == R_VCOMPAT ? "converted video" : "audio", seg, err);
        }
        pthread_mutex_lock(&P.lock);
        // Clear ownership before another request can acquire the lane. Otherwise a seeker can mistake
        // the new foreground converter for this finished background job and cancel the wrong work.
        P.busy_rend[me] = -1; P.busy_seg[me] = -1;
        pthread_mutex_unlock(l);
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
    atomic_fetch_add(&demand[rend], 1);
    if (seg >= 0) prefetch_focus(rend, seg);
    // Cancel only a background job identified under P.lock. Concurrent foreground requests (including
    // retries/init reads by the phone and TV) must not cancel each other and turn a seek into HTTP 500.
    double queued = now_ms();
    while(pthread_mutex_trylock(l)!=0) {
        // An encoder can publish its init while still producing media under this lane's lock.
        if(seg<0 && cache_take(rend,seg,out)){atomic_fetch_sub(&demand[rend],1);return 0;}
        if(atomic_load(&S.stopping)){atomic_fetch_sub(&demand[rend],1);snprintf(err,(size_t)errlen,"stopping");return -1;}
        usleep(10000);
    }
    double began = now_ms();
    int r = cache_take(rend, seg, out) ? 0 : make_part(rend, seg < 0 ? 0 : seg, 0, seg < 0, out, err, errlen);
    pthread_mutex_unlock(l);
    atomic_fetch_sub(&demand[rend], 1);
    double ended = now_ms();
    if (began - queued > 250 || ended - began > 1000)
        log_line("request: %s segment %d waited %.0f ms, production %.0f ms, result %d",
                 rend == R_VCOPY ? "video" : rend == R_VCOMPAT ? "converted video" : "audio", seg,
                 began - queued, ended - began, r);
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


// Prepared-file requests share the movie byte cache with the probing and subtitle cursors. A cache hit
// bypasses this connection lock, so a header request cannot queue behind another client's remote read.
static struct { pthread_mutex_t lock; kr_source *src; } PC = {PTHREAD_MUTEX_INITIALIZER};
static void prepared_cache_clear(void) {
    pthread_mutex_lock(&PC.lock);publish_source(&prepared_source,NULL);
    kr_source_close(PC.src);PC.src=NULL;pthread_mutex_unlock(&PC.lock);
}
static int prepared_read(int64_t offset,uint8_t *buf,int want,char *error,int errlen) {
    (void)error;(void)errlen;
    int r=kr_source_cached_read(S.src,offset,buf,want);if(r>0)return r;
    pthread_mutex_lock(&PC.lock);
    if(!PC.src) {
        PC.src=kr_source_clone(S.src,15,source_interrupted,(void *)(uintptr_t)atomic_load(&S.ticket));
        publish_source(&prepared_source,PC.src);
    }
    double at=now_ms(),io=kr_source_io_ms(PC.src);
    r=PC.src?kr_source_read(PC.src,offset,buf,want):-1;
    double spent=kr_source_io_ms(PC.src)-io;
    if(now_ms()-at>1000)log_line("source: range at %lld returned %d B in %.0f ms, source I/O %.0f ms",(long long)offset,r,now_ms()-at,spent);
    pthread_mutex_unlock(&PC.lock);return r;
}
// Warm at most 1 MiB using an independent cursor. Demand reads can take cached prefixes immediately;
// warming never owns the foreground connection or a multi-megabyte cache lock.
static void *prepared_warm(void *arg) {
    unsigned ticket=(unsigned)(uintptr_t)arg;double at=now_ms();int filled=0;
    kr_source *src=kr_source_clone(S.src,8,source_interrupted,arg);
    uint8_t buf[65536];
    while(src && filled<1024*1024 && filled<S.prepared_size && !source_interrupted(arg) && now_ms()-at<8000) {
        int n=kr_source_read(src,filled,buf,sizeof buf);if(n<=0)break;filled+=n;
    }
    kr_source_close(src);
    if(ticket==atomic_load(&S.ticket))log_line("prepared: cached %d startup bytes in %.0f ms",filled,now_ms()-at);
    atomic_fetch_sub(&S.active,1);return NULL;
}
static void prepared_warm_start(unsigned ticket) {
    pthread_t thread;atomic_fetch_add(&S.active,1);
    if(pthread_create(&thread,NULL,prepared_warm,(void *)(uintptr_t)ticket)){atomic_fetch_sub(&S.active,1);return;}
    pthread_detach(thread);
}
static void serve_prepared(int fd,int head,const char *range,const char *agent) {
    int64_t size=S.prepared_size,first=0,last=size-1;int partial=range!=NULL,valid=size>0;
    if(range) {
        if(strncmp(range,"bytes=",6) || strchr(range,','))valid=0;
        else if(range[6]=='-') {
            char *end=NULL;long long suffix=strtoll(range+7,&end,10);
            if(suffix<=0 || !end || *end)valid=0;else first=suffix>=size?0:size-suffix;
        } else {
            char *end=NULL;first=strtoll(range+6,&end,10);
            if(first<0 || !end || *end!='-')valid=0;
            else if(end[1]) {char *tail=NULL;last=strtoll(end+1,&tail,10);if(!tail || *tail || last<first)valid=0;}
            if(last>=size)last=size-1;
        }
        if(first>=size)valid=0;
    }
    char header[512];int length;
    if(!valid) {
        length=snprintf(header,sizeof header,"HTTP/1.1 416 Range Not Satisfiable\r\nContent-Range: bytes */%lld\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",(long long)size);
        send_all(fd,header,(size_t)length);t_status=416;return;
    }
    length=partial?snprintf(header,sizeof header,"HTTP/1.1 206 Partial Content\r\nContent-Type: video/mp4\r\nContent-Length: %lld\r\nContent-Range: bytes %lld-%lld/%lld\r\nAccept-Ranges: bytes\r\nConnection: close\r\n\r\n",(long long)(last-first+1),(long long)first,(long long)last,(long long)size):
        snprintf(header,sizeof header,"HTTP/1.1 200 OK\r\nContent-Type: video/mp4\r\nContent-Length: %lld\r\nAccept-Ranges: bytes\r\nConnection: close\r\n\r\n",(long long)size);
    t_status=partial?206:200;
    if(send_all(fd,header,(size_t)length)){t_status=-t_status;return;}
    if(head)return;
    char error[128]="";
    uint8_t buffer[65536];int counted=0;
    while(first<=last && !atomic_load(&S.stopping)) {
        int want=(int)((last-first+1)>(int64_t)sizeof buffer?sizeof buffer:last-first+1);
        int got=prepared_read(first,buffer,want,error,sizeof error);
        if(got<=0){t_status=-t_status;snprintf(t_err,sizeof t_err,"Prepared file read unavailable");break;}
        if(send_all(fd,buffer,(size_t)got)){t_status=-t_status;break;}
        t_bytes+=(size_t)got;first+=got;
        if(t_bytes>65536) {
            media_sent(1);
            if(!counted) {
                counted=1;atomic_fetch_add(&S.served_video,1);atomic_fetch_add(&S.served_audio,1);
                if(!phone_player(agent)){atomic_fetch_add(&S.served_ext_video,1);atomic_fetch_add(&S.served_ext_audio,1);}
            }
        }
    }
}

static void serve(int fd, const char *method, const char *path, const char *range, const char *agent) {
    int head = !strcmp(method, "HEAD");
    if(S.prepared) {
        const char *list=!strcmp(path,"/prepared.m3u8")?S.prepared_master:!strcmp(path,"/prepared-media.m3u8")?S.prepared_media:NULL;
        if(list){respond(fd,head,NULL,"application/vnd.apple.mpegurl",(const uint8_t *)list,strlen(list));return;}
        if(!strcmp(path,"/prepared.mp4")){serve_prepared(fd,head,range,agent);return;}
        if(strncmp(path,"/subs/",6)){fail(fd,404,"Not Found");return;}   // r38: WebVTT renditions, below
    }
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
        double cue_deadline=now_ms()+1500;
        if (!burned) for (int k = 0; k < 15 && !atomic_load(&S.stopping); k++) {  // up to ~1.5 s for a cue file in progress
            if (pthread_mutex_trylock(&S.sgm_lock) == 0) { got = 1; break; }
            usleep(100000);
        }
        r = -1;
        if (got) {
            atomic_store(&S.subtitle_deadline_ms,(long long)cue_deadline);
            gm_stream *g = subs_demuxer();
            if (g) r = gm_stream_subtitle_segment(g, idx, seg, &buf, err, sizeof err);
            if(now_ms()>=cue_deadline) {
                gm_stream_close(S.sgm);S.sgm=NULL;
                kr_source *gone=S.ssrc;publish_source(&S.ssrc,NULL);kr_source_close(gone);
                S.sgm_failed=0;r=-1;
            }
            atomic_store(&S.subtitle_deadline_ms,0);
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
    if (getifaddrs(&list) != 0) { log_line("network: getifaddrs failed errno=%d",errno); return -1; }
    for (struct ifaddrs *i = list; i; i = i->ifa_next) {
        if (!i->ifa_addr || i->ifa_addr->sa_family != AF_INET || !(i->ifa_flags & IFF_UP) || (i->ifa_flags & IFF_LOOPBACK)) continue;
        if (!strcmp(i->ifa_name, "en0")) { best = i; break; }
#ifndef __APPLE__
        if (!best) best = i;  // host tests: iOS must never advertise a cellular/VPN address as Wi-Fi
#endif
    }
    int r = -1;
    if (best && inet_ntop(AF_INET, &((struct sockaddr_in *)best->ifa_addr)->sin_addr, out, (socklen_t)len)) r = 0;
    if (!r) log_line("network: interface=%s IPv4=%s",best->ifa_name,out);
    else log_line("network: no usable Wi-Fi en0 IPv4");
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
    int slot=(int)(intptr_t)arg;
    pthread_mutex_lock(&CLIENTS.lock);int fd=CLIENTS.fd[slot]-1;pthread_mutex_unlock(&CLIENTS.lock);
    char req[8192]; size_t got = 0;
    while (got < sizeof req - 1) {
        ssize_t n = recv(fd, req + got, sizeof req - 1 - got, 0);
        if (n <= 0) break;
        got += (size_t)n; req[got] = 0;
        if (strstr(req, "\r\n\r\n")) break;
    }
    req[got] = 0;
    struct sockaddr_in peer={0};socklen_t peerlen=sizeof peer;char peer_ip[INET_ADDRSTRLEN]="unknown";
    if (!getpeername(fd,(struct sockaddr *)&peer,&peerlen)) inet_ntop(AF_INET,&peer.sin_addr,peer_ip,sizeof peer_ip);
    char method[8] = "", path[1024] = "", version[16]="";
    int parsed=sscanf(req, "%7s %1023s %15s", method, path, version);
    char *q = strchr(path, '?'); if (q) *q = 0;
    size_t tl = strlen(S.token);
    int ok = path[0] == '/' && !strncmp(path + 1, S.token, tl) && path[1 + tl] == '/';
    if(parsed>=2) log_line("request: peer=%s %s /[token]%s %s",peer_ip,method,
                          ok ? path+1+tl : "/[unrecognized]",!strncmp(version,"HTTP/",5) ? version : "[no HTTP version]");
    else if(got) log_line("request: peer=%s [malformed request line]",peer_ip);
    if (parsed >= 2 && (!strcmp(method, "GET") || !strcmp(method, "HEAD"))) {
        char range[128] = "", agent[160] = "", *h = req;
        while ((h = strstr(h, "\r\n")) != NULL) {
            h += 2;
            if (!strncasecmp(h, "Range:", 6)) sscanf(h + 6, " %127[^\r\n]", range);
            else if (!strncasecmp(h, "User-Agent:", 11)) sscanf(h + 11, " %159[^\r\n]", agent);
        }
        log_agent(agent);
        t_status = 0; t_bytes = 0; t_err[0] = 0;t_tv=0;t_media_marked=0;
        double t0 = now_ms();
        // Before serve(): a slow source must not make an arrived TV request look like a network failure.
        pthread_mutex_lock(&N.lock);
        int tv=ok && N.expected && N.ticket==atomic_load(&S.ticket) && N.ticket==atomic_load(&request_ticket) &&
               kr_remux_external_peer(peer_ip,N.host,agent);
        if(tv) {
            N.tv_requests++;
            if(!N.tv_video)N.phase="connecting";
            if(!N.connect_ms)N.connect_ms=now_ms();
            if(!N.first_tv_ms) {
                N.first_tv_ms=now_ms();
                log_line("network: first TV request peer=%s after %.0f ms from start",peer_ip,N.first_tv_ms-N.start_ms);
            }
        }
        pthread_mutex_unlock(&N.lock);
        t_tv=tv;
        if (ok) serve(fd, method, path + 1 + tl, *range ? range : NULL, agent);
        else fail(fd, 404, "Not Found");
        const char *part=ok?path+1+tl:"";
        int media=strstr(part,".m4s")!=NULL || (!strcmp(part,"/prepared.mp4") && t_bytes>65536);
        if(tv && !strcmp(method,"GET") && media && t_status>0 && t_bytes>0) {
            media_sent(strncmp(part,"/audio/",7)!=0);
        }
        // "GET /video/seg3.m4s 200 1834567 B 412 ms"
        log_line("%s %s%s%s %d %zu B %.0f ms%s%s", method, ok ? path + 1 + tl : "(no token)", *range ? " " : "", range,
                 t_status, t_bytes, now_ms() - t0, *t_err ? ": " : "", t_err);
    } else fail(fd, 405, "Method Not Allowed");
    pthread_mutex_lock(&CLIENTS.lock);close(fd);CLIENTS.fd[slot]=0;pthread_mutex_unlock(&CLIENTS.lock);
    atomic_fetch_sub(&S.active, 1);
    return NULL;
}

static void *accept_loop(void *unused) {
    (void)unused;
    while (!atomic_load(&S.stopping)) {
        struct sockaddr_in peer={0};socklen_t len=sizeof peer;
        int fd = accept(S.listen_fd, (struct sockaddr *)&peer, &len);
        if (fd < 0) { if (errno == EINTR) continue; break; }
        char ip[INET_ADDRSTRLEN]="unknown";inet_ntop(AF_INET,&peer.sin_addr,ip,sizeof ip);
        log_line("accept: peer=%s:%d",ip,ntohs(peer.sin_port));
        if (atomic_load(&S.stopping)) { close(fd); break; }
        int slot=-1;
        pthread_mutex_lock(&CLIENTS.lock);
        for(int i=0;i<CONNECTION_LIMIT;i++)if(!CLIENTS.fd[i]){slot=i;CLIENTS.fd[i]=fd+1;break;}
        pthread_mutex_unlock(&CLIENTS.lock);
        if(slot<0){close(fd);continue;}
#ifdef SO_NOSIGPIPE
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof one);
#endif
        struct timeval tv = { 60, 0 };
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
        atomic_fetch_add(&S.active, 1);
        pthread_t t;
        pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
        if (pthread_create(&t, &at, connection, (void *)(intptr_t)slot) != 0) {
            pthread_mutex_lock(&CLIENTS.lock);close(fd);CLIENTS.fd[slot]=0;pthread_mutex_unlock(&CLIENTS.lock);
            atomic_fetch_sub(&S.active, 1);
        }
        pthread_attr_destroy(&at);
    }
    return NULL;
}

// Binds all interfaces for AirPlay, loopback for phone playback, on a system-selected port.
static int listen_on(int lan, int *port) {
    for (int attempt = 0; attempt < 5; attempt++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) { log_line("server: socket failed errno=%d",errno); continue; }
        int one = 1; setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        struct sockaddr_in a = { 0 };
        a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(lan ? INADDR_ANY : INADDR_LOOPBACK); a.sin_port = 0;
        socklen_t len = sizeof a;
        if (bind(fd, (struct sockaddr *)&a, sizeof a) == 0 && listen(fd, 32) == 0 &&
            getsockname(fd, (struct sockaddr *)&a, &len) == 0) {
            *port = ntohs(a.sin_port);
            pthread_mutex_lock(&N.lock);
            if(N.ticket==atomic_load(&S.ticket) && N.ticket==atomic_load(&request_ticket)) {
                N.port=*port;N.listen_ms=now_ms();
            }
            pthread_mutex_unlock(&N.lock);
            log_line("server: listening bind=%s port=%d result=ok",lan ? "0.0.0.0" : "127.0.0.1",*port);
            return fd;
        }
        log_line("server: listen attempt=%d bind=%s failed errno=%d",attempt+1,lan ? "0.0.0.0" : "127.0.0.1",errno);
        close(fd);
    }
    return -1;
}

static void teardown_locked(void) {
    abort_sources();
    if (S.listen_fd >= 0) {
        shutdown(S.listen_fd, SHUT_RDWR); close(S.listen_fd); S.listen_fd = -1;
        pthread_join(S.accept_thread, NULL);
    }
    pthread_mutex_lock(&CLIENTS.lock);
    for(int i=0;i<CONNECTION_LIMIT;i++)if(CLIENTS.fd[i])shutdown(CLIENTS.fd[i]-1,SHUT_RDWR);
    pthread_mutex_unlock(&CLIENTS.lock);
    prefetch_stop();  // r8: background producers end (their reads fail now) before anything is freed
    while(atomic_load(&S.active)>0)usleep(10000); // sockets and sources are interrupted; never free a live session
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
    kr_source *source=S.src;publish_source(&S.src,NULL);kr_source_close(source);
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
    pthread_mutex_lock(&src_lock);S.nbridges = 0;pthread_mutex_unlock(&src_lock);S.port = 0;
    pthread_mutex_lock(&S.vlock);  // a request still converting has finished or given up (abort above)
    pthread_mutex_lock(&src_lock);
    kr_video *video = S.video; kr_source *vsrc = S.vsrc;
    S.video = NULL; S.vsrc = NULL;
    pthread_mutex_unlock(&src_lock);
    kr_video_close(video);
    kr_source_close(vsrc);
    pthread_mutex_unlock(&S.vlock);
    S.compat = 0; S.vindex = -1; S.compat_ok = 0;S.prepared=0;S.prepared_size=0;
    free(S.prepared_master);S.prepared_master=NULL;free(S.prepared_media);S.prepared_media=NULL;
    prepared_cache_clear();   // r29
    atomic_store(&S.vlogged, 0);
    free(S.master_copy); S.master_copy = NULL;
    free(S.master_compat); S.master_compat = NULL;
    for (int i = 0; i < MAX_TRACKS; i++) S.routes[i] = KR_AUDIO_NONE;
    cache_clear();
}

void kr_remux_stop_for(unsigned ticket) {
    pthread_mutex_lock(&S.lock);
    if(!ticket || ticket==atomic_load(&S.ticket)) {
        teardown_locked();
        atomic_store(&S.state, KR_IDLE);
        set_message("");
    }
    pthread_mutex_unlock(&S.lock);
}

void kr_remux_stop(void) { kr_remux_cancel(0);kr_remux_stop_for(0); }

static int needs_video_conversion(const AVCodecParameters *cp) {
    if (cp->codec_id != AV_CODEC_ID_H264 && cp->codec_id != AV_CODEC_ID_HEVC) return 0;
    int depth = cp->codec_id == AV_CODEC_ID_H264 ? 8 : 10;
    const AVPixFmtDescriptor *pf = av_pix_fmt_desc_get(cp->format);
    if (cp->bits_per_raw_sample > depth || (pf && (pf->comp[0].depth > depth || pf->log2_chroma_w != 1 || pf->log2_chroma_h != 1))) return 1;
    if (cp->codec_id == AV_CODEC_ID_H264 && cp->profile >= 0 && (cp->profile & ~AV_PROFILE_H264_CONSTRAINED) > AV_PROFILE_H264_HIGH) return 1;
    return cp->codec_id == AV_CODEC_ID_HEVC && cp->profile > AV_PROFILE_HEVC_MAIN_STILL_PICTURE;
}

// r38 (owner's build-201 log, Apple TV): given prepared.mp4 itself, Apple's player walked the 7 GB file fragment by
// fragment (ranges at 73 MB, 112 MB, 136 MB... each a new Drive read of 3-6 s), never became ready and never handed the
// movie to the Apple TV: a black screen. AVFoundation reads every moof of a progressive fragmented MP4 (it does not use
// the mfra index; karbassi/undertone#8 measured the same). The same bytes as HLS: the init (ftyp+moov) as EXT-X-MAP and
// one EXT-X-BYTERANGE per fragment (moof+mdat), taken from the file's own fragment index (the mfra kr_prepare writes).
// Apple's player and the TV then fetch only what plays. 0 on success; the plain MP4 stays the fallback.
static int prepared_read_all(int64_t at,uint8_t *buf,int len) {
    char e[64];int done=0;
    while(done<len){int got=prepared_read(at+done,buf+done,len-done,e,sizeof e);if(got<=0)return -1;done+=got;}
    return 0;
}
typedef struct {int64_t time,offset;} prep_frag;
static int prepared_playlists(int align_plan) {
    AVFormatContext *f=gm_stream_format_context(S.gm);
    int v=gm_stream_selected_video(S.gm);
    if(!f || v<0 || v>=(int)f->nb_streams || S.prepared_size<64)return -1;
    AVStream *st=f->streams[v];
    if(st->time_base.num<=0 || st->time_base.den<=0)return -1;
    uint8_t tail[16];
    if(prepared_read_all(S.prepared_size-16,tail,16) || memcmp(tail+4,"mfro",4))return -1;
    uint32_t mfra_size=AV_RB32(tail+12);
    if(mfra_size<16 || mfra_size>16*1024*1024 || (int64_t)mfra_size>S.prepared_size)return -1;
    int64_t mfra_at=S.prepared_size-mfra_size;
    uint8_t *m=malloc(mfra_size);if(!m)return -1;
    prep_frag *fr=NULL;int n=0,cap=0,ok=-1;char *media=NULL,*master=NULL;
    if(prepared_read_all(mfra_at,m,(int)mfra_size) || memcmp(m+4,"mfra",4))goto end;
    for(uint32_t at=8;at+8<=mfra_size;) {
        uint32_t size=AV_RB32(m+at);
        if(size<8 || at+size>mfra_size)break;
        if(!memcmp(m+at+4,"tfra",4) && size>=24 && (int)AV_RB32(m+at+12)==st->id) {
            int version=m[at+8];uint32_t lengths=AV_RB32(m+at+16),count=AV_RB32(m+at+20);
            int skip=(int)(((lengths>>4)&3)+((lengths>>2)&3)+(lengths&3)+3),entry=(version==1?16:8)+skip;
            if((uint64_t)24+(uint64_t)count*(uint64_t)entry>size)goto end;
            for(uint32_t i=0;i<count;i++) {
                const uint8_t *e=m+at+24+i*(uint32_t)entry;
                int64_t t=version==1?(int64_t)AV_RB64(e):AV_RB32(e),o=version==1?(int64_t)AV_RB64(e+8):AV_RB32(e+4);
                if(n && (o<=fr[n-1].offset || t<fr[n-1].time))goto end;   // the index must run forward
                if(n==cap){cap=cap?cap*2:512;prep_frag *g=realloc(fr,sizeof *g*(size_t)cap);if(!g)goto end;fr=g;}
                fr[n++]=(prep_frag){t,o};
            }
        }
        at+=size;
    }
    if(n<1 || fr[0].offset<16 || fr[n-1].offset>=mfra_at)goto end;
    double tb=av_q2d(st->time_base),total=gm_stream_duration(S.gm);
    if(align_plan) {
        double *times=malloc((size_t)n*sizeof *times);if(!times)goto end;
        for(int i=0;i<n;i++)times[i]=(double)fr[i].time*tb;
        ok=gm_stream_plan_keyframes(S.gm,times,n);free(times);
        if(!ok)log_line("segmented: using %d indexed random-access windows; old long-GOP movies retain their real durations",gm_stream_segment_count(S.gm));
        goto end;
    }
    double end_time=total>0?total+(double)fr[0].time*tb:0;
    if(st->duration>0 && st->duration!=AV_NOPTS_VALUE)end_time=(double)(st->duration+fr[0].time)*tb;
    double longest=0,peak=0;
    AVBPrint b;av_bprint_init(&b,0,AV_BPRINT_SIZE_UNLIMITED);
    for(int i=0;i<n;i++) {
        double d=(i+1<n?(double)(fr[i+1].time-fr[i].time)*tb:end_time-(double)fr[i].time*tb);
        if(d<=0)d=0.04;
        int64_t len=(i+1<n?fr[i+1].offset:mfra_at)-fr[i].offset;
        if(d>longest)longest=d;
        if(d>=1 && (double)len*8/d>peak)peak=(double)len*8/d;
        av_bprintf(&b,"#EXTINF:%.3f,\n#EXT-X-BYTERANGE:%lld@%lld\n%s/prepared.mp4\n",d,(long long)len,(long long)fr[i].offset,S.base);
    }
    AVBPrint h;av_bprint_init(&h,0,AV_BPRINT_SIZE_UNLIMITED);
    av_bprintf(&h,"#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-TARGETDURATION:%d\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-INDEPENDENT-SEGMENTS\n"
               "#EXT-X-MAP:URI=\"%s/prepared.mp4\",BYTERANGE=\"%lld@0\"\n%s#EXT-X-ENDLIST\n",(int)ceil(longest),S.base,(long long)fr[0].offset,b.str);
    av_bprint_finalize(&b,NULL);
    if(av_bprint_finalize(&h,&media)<0 || !media)goto end;
    // Muxed segments: CODECS lists the picture and every audio codec in the file; no separate renditions.
    char tokens[128]="";
    int tracks=gm_stream_track_count(S.gm);gm_track_info t;
    for(int i=0;i<tracks;i++) {
        if(gm_stream_track_info(S.gm,i,&t)!=0 || t.kind!=GM_TRACK_AUDIO || kr_audio_route(&t)!=KR_AUDIO_COPY)continue;
        const char *tok=kr_audio_token(&t);
        if(tok && *tok && !strstr(tokens,tok) && strlen(tokens)+strlen(tok)+2<sizeof tokens){strcat(tokens,",");strcat(tokens,tok);}
    }
    double fps=0;AVRational r=st->avg_frame_rate.num>0 && st->avg_frame_rate.den>0?st->avg_frame_rate:st->r_frame_rate;
    if(r.num>0 && r.den>0)fps=av_q2d(r);
    gm_color_info c;const char *range="SDR";
    if(gm_stream_color_info(S.gm,&c)==0 && gm_stream_is_hdr(S.gm))range=c.transfer==18?"HLG":"PQ";
    double average=end_time>0?(double)(mfra_at-fr[0].offset)*8/(end_time-(double)fr[0].time*tb):0;
    // r39 (owner, build 202: "subtitles didnt work"): the file's text subtitles (mov_text) ride in the fragments, which
    // HLS ignores; they go as WebVTT renditions (the converted path's /subs/ playlists and cue files). The one Kodi
    // shows (else the file's forced/default) is DEFAULT, and the native player selects it.
    AVBPrint subs;av_bprint_init(&subs,0,AV_BPRINT_SIZE_UNLIMITED);int nsub=0;
    {
        pthread_mutex_lock(&SUBS.lock);int ord=SUBS.ordinal;char lang[16];snprintf(lang,sizeof lang,"%s",SUBS.lang);pthread_mutex_unlock(&SUBS.lock);
        int pick=ord==-1?-1:kr_subs_pick(f,ord,lang),first=-1;
        for(int i=0;i<tracks;i++)if(gm_stream_track_info(S.gm,i,&t)==0 && t.kind==GM_TRACK_SUBTITLE && t.is_text_sub){first=t.src_index;break;}
        if(pick<0 && ord!=-1)pick=first;
        char used[16][100];
        for(int i=0;i<tracks && nsub<16;i++) {
            if(gm_stream_track_info(S.gm,i,&t)!=0 || t.kind!=GM_TRACK_SUBTITLE || !t.is_text_sub)continue;
            char name[100];const char *code=kr_language(t.language);
            if(t.title[0])snprintf(name,sizeof name,"%.80s",t.title);else if(*code)snprintf(name,sizeof name,"%s",t.language);else snprintf(name,sizeof name,"Subtitles %d",nsub+1);
            for(char *c=name;*c;c++)if(*c=='"' || *c=='\n' || *c=='\r')*c='\'';
            for(int k=0;k<nsub;k++)if(!strcmp(used[k],name)){char tmp[100];snprintf(tmp,sizeof tmp,"%.80s #%d",name,nsub+1);snprintf(name,sizeof name,"%s",tmp);break;}
            snprintf(used[nsub++],sizeof used[0],"%s",name);
            av_bprintf(&subs,"#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID=\"subs\",NAME=\"%s\"",name);
            if(*code)av_bprintf(&subs,",LANGUAGE=\"%s\"",code);
            av_bprintf(&subs,",DEFAULT=%s,AUTOSELECT=YES,FORCED=NO,URI=\"%s/subs/%d/index.m3u8\"\n",t.src_index==pick?"YES":"NO",S.base,t.src_index);
        }
        if(nsub)log_line("prepared: %d text subtitle track(s) as WebVTT%s",nsub,pick>=0?", Kodi's on":"");
    }
    AVBPrint x;av_bprint_init(&x,0,AV_BPRINT_SIZE_UNLIMITED);
    // The renditions go before the variant that names their group.
    av_bprintf(&x,"#EXTM3U\n#EXT-X-VERSION:7\n#EXT-X-INDEPENDENT-SEGMENTS\n%s#EXT-X-STREAM-INF:BANDWIDTH=%ld",subs.str,(long)fmax(peak,average>0?average:8e6));
    if(average>0)av_bprintf(&x,",AVERAGE-BANDWIDTH=%ld",(long)average);
    av_bprintf(&x,",CODECS=\"%s%s\"",S.vcodec,tokens);
    if(st->codecpar->width>0 && st->codecpar->height>0)av_bprintf(&x,",RESOLUTION=%dx%d",st->codecpar->width,st->codecpar->height);
    if(fps>0)av_bprintf(&x,",FRAME-RATE=%.3f",fps);
    if(nsub)av_bprintf(&x,",SUBTITLES=\"subs\"");
    av_bprintf(&x,",VIDEO-RANGE=%s\n%s/prepared-media.m3u8\n",range,S.base);
    av_bprint_finalize(&subs,NULL);
    if(av_bprint_finalize(&x,&master)<0 || !master)goto end;
    log_line("prepared: HLS over the file's %d fragments (byte ranges, longest %.1f s, peak %.1f Mbit/s, %s, %s%s)",n,longest,peak/1e6,range,S.vcodec,tokens);
    S.prepared_master=master;S.prepared_media=media;master=media=NULL;ok=0;
end:
    if(ok && !align_plan)log_line("prepared: no usable fragment index; Apple's player gets the MP4 itself");
    free(m);free(fr);av_free(media);av_free(master);
    return ok;
}

int kr_remux_start_for(unsigned ticket,const char *url, int lan, int compat, char *out, int outlen) {
    if(out && outlen>0)*out=0;
    pthread_mutex_lock(&S.lock);
    if(ticket!=atomic_load(&request_ticket)){pthread_mutex_unlock(&S.lock);return KR_FAILED;}
    teardown_locked();
    if(ticket!=atomic_load(&request_ticket)){pthread_mutex_unlock(&S.lock);return KR_FAILED;}
    atomic_store(&S.ticket,ticket);
    network_begin_for(lan,ticket);
    atomic_store(&S.stopping, 0);
    atomic_store(&S.startup_deadline_ms,(long long)(now_ms()+45000));
    atomic_store(&S.served_video, 0); atomic_store(&S.served_audio, 0); S.vcodec[0] = 0;
    atomic_store(&S.compat_clients, 0); atomic_store(&S.prefetched, 0);
    atomic_store(&S.served_ext_video, 0); atomic_store(&S.served_ext_audio, 0);
    atomic_store(&S.state, KR_STARTING);
    set_message("");
    if (out && outlen > 0) *out = 0;
    char err[256] = "";
    int result = KR_FAILED;
    snprintf(S.url, sizeof S.url, "%s", url ? url : "");
    pthread_mutex_lock(&L.lock); memset(L.agents, 0, sizeof L.agents); pthread_mutex_unlock(&L.lock);
    log_line("start: %.*s", (int)(strcspn(S.url, "?") < 200 ? strcspn(S.url, "?") : 200), S.url);  // no query (tokens)
    double source_at=now_ms();
    publish_source(&S.src,kr_source_open_interruptible(S.url,30,source_interrupted,(void *)(uintptr_t)ticket,err,sizeof err));
    log_line("startup: source opened after %.0f ms (attempt %u)",now_ms()-source_at,ticket);
    if (!S.src) { char m[300]; snprintf(m, sizeof m, "AirPlay: %s.", err); set_message(m); goto done; }
    {   // Adaptive playlists remain native. File containers, including MP4/MOV, must reach codec/receiver routing.
        uint8_t pad[4096] = {0};
        int n = kr_source_read(S.src, 0, pad, 4096);
        int bom = n >= 3 && pad[0] == 0xef && pad[1] == 0xbb && pad[2] == 0xbf ? 3 : 0;
        if (n >= bom + 7 && !memcmp(pad + bom, "#EXTM3U", 7)) { result = KR_NOT_NEEDED; goto done; }
    }
    phase_for(ticket,"inspecting");
    double inspect_at=now_ms();
    S.gm = gm_stream_open(kr_source_gm(S.src), SEG_SECONDS, err, sizeof err);
    log_line("startup: indexed inspection finished after %.0f ms (attempt %u)",now_ms()-inspect_at,ticket);
    if(source_interrupted((void *)(uintptr_t)ticket))goto done;
    if (!S.gm) {
        char m[300];
        snprintf(m, sizeof m, "AirPlay cannot play this file: %s.", *err ? err : "the video is not H.264 or HEVC");
        set_message(m);
        goto done;
    }
    // Fully prepared, indexed MP4: AVPlayer seeks the one Drive file directly. In particular do not
    // assume all third-party receivers require 1080p H.264, or burn subtitles/transcode after a seek.
    // r36 (owner's build-198 log and photo: a TCL Roku TV showed a music note and played only the sound of a
    // prepared HEVC movie): when the player asks again in compat mode, that TV cannot take this picture, so the
    // prepared file goes through the H.264 conversion like any other source instead of being served again as it is.
    // r41 (ISSUE-138): KR_COMPAT_SEGMENTED, for a Roku's own player: the prepared movie goes through the remuxer like
    // any other file (picture copied, 6-s segments, audio as its own rendition) instead of as-is. Roku's streaming
    // specifications: CMAF HLS with audio and video muxed together is not supported, chunks of 4-6 s (< 10 s VOD)
    // are recommended; the prepared file's fragments carry both and run up to 70 s.
    const int segmented = compat == KR_COMPAT_SEGMENTED;
    if (segmented) {
        compat = 0;
        log_line("segmented: a TV's own player gets 6-s segments with the audio apart (picture copied)");
    }
    AVFormatContext *prepared=gm_stream_format_context(S.gm);
    if(segmented && prepared && prepared->iformat && strstr(prepared->iformat->name,"mov")) {
        S.prepared_size=kr_source_size(S.src);
        // Copying cannot create keyframes. A uniform six-second grid repeats/skips pictures when the source
        // has 30-second GOPs. Its complete fragment index supplies real, independently decodable boundaries.
        prepared_playlists(1);
    }
    if(!compat && !segmented && kr_prepare_ready(prepared) && av_dict_get(prepared->metadata,"kodi_airplay_prepared",NULL,0)) {
        char host[64]="127.0.0.1";
        if(lan && lan_address(host,sizeof host)){set_message("AirPlay needs Wi-Fi.");goto done;}
        S.prepared_size=kr_source_size(S.src);
        if(S.prepared_size<=0){set_message("Prepared file size is unavailable.");goto done;}
        prepared_cache_clear();S.prepared=1;S.listen_fd=listen_on(lan,&S.port);
        if(S.listen_fd<0){set_message("AirPlay file server could not start.");goto done;}
        random_token(S.token,sizeof S.token);
        snprintf(S.base,sizeof S.base,"http://%s:%d/%s",host,S.port,S.token);
        pthread_mutex_lock(&N.lock);
        if(N.ticket==ticket && ticket==atomic_load(&request_ticket))snprintf(N.host,sizeof N.host,"%s",host);
        pthread_mutex_unlock(&N.lock);
        log_line("server: endpoint=%s:%d/[token]/prepared.mp4",host,S.port);
        kr_hls_video_codec(S.gm,S.vcodec,sizeof S.vcodec);
        prepared_playlists(0);
        prepared_warm_start(ticket);   // r41: the init and the first fragment's start, before the TV asks
        if(pthread_create(&S.accept_thread,NULL,accept_loop,NULL)){close(S.listen_fd);S.listen_fd=-1;goto done;}
        if(out && outlen>0)snprintf(out,(size_t)outlen,"%s/prepared.%s",S.base,S.prepared_master?"m3u8":"mp4");
        log_line("prepared: source-resolution MP4 byte ranges; no live conversion, subtitle burn or prefetch queue");
        result=KR_READY;goto done;
    }
    // Profile 5 has no ordinary HDR base layer. Route it through RPU-aware SDR conversion so third-party
    // receivers do not inherit the phone's native Dolby capability or display unreshaped IPT pixels.
    gm_color_info colors;
    AVFormatContext *original = gm_stream_format_context(S.gm);
    if (!compat && original && gm_stream_color_info(S.gm, &colors) == 0 &&
        colors.dolby_vision && colors.dovi_profile == 5) {
        compat=1;
        log_line("compat: Dolby Vision profile 5 uses RPU-aware SDR conversion");
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
            pthread_mutex_lock(&src_lock);
            bridge *b = &S.bridges[S.nbridges++];
            memset(b, 0, sizeof *b); b->index = t.src_index; pthread_mutex_init(&b->lock, NULL);
            pthread_mutex_unlock(&src_lock);
        }
    }
    // r7: compat mode converts the picture. Asked for (the TV played sound only), or needed: the file's video is not
    // one AirPlay carries (VP9, MPEG-2...) but FFmpeg decodes it.
    S.vindex = kr_video_pick_stream(S.gm);
    AVFormatContext *input = gm_stream_format_context(S.gm);
    int has_video = 0;
    for (unsigned i = 0; input && i < input->nb_streams; i++)
        if (input->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO &&
            !(input->streams[i]->disposition & AV_DISPOSITION_ATTACHED_PIC)) has_video = 1;
    int selected = gm_stream_selected_video(S.gm);
    if (!compat && has_video && (selected < 0 || needs_video_conversion(input->streams[selected]->codecpar))) {
        if (S.vindex < 0) { set_message("AirPlay: this build cannot decode this video's codec."); goto done; }
        if (!kr_video_available()) { set_message("AirPlay: this build cannot convert video (no H.264 encoder)."); goto done; }
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
        snprintf(S.burn_language, sizeof S.burn_language, "%s", lang);
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
        S.compat_ok = !S.compat && v >= 0 && S.vindex >= 0 && f &&
                      (burn || f->streams[v]->codecpar->codec_id != AV_CODEC_ID_H264 ||
                       f->streams[v]->codecpar->width > 1920 || f->streams[v]->codecpar->height > 1080) &&
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
    pthread_mutex_lock(&N.lock);
    if(N.ticket==ticket && ticket==atomic_load(&request_ticket))snprintf(N.host,sizeof N.host,"%s",host);
    pthread_mutex_unlock(&N.lock);
    log_line("server: endpoint=%s:%d/[token]/master.m3u8",host,S.port);
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
    // Publish copied-track headers before any producer can own a lane. These use codec metadata only,
    // so the receiver's init request never waits for a full six-second segment from Drive.
    for(int i=0;i<gm_stream_track_count(S.gm);i++) {
        gm_track_info t;gm_buf init={0};char e[128]="";
        if(gm_stream_track_info(S.gm,i,&t)!=0 || t.src_index<0 || t.src_index>=MAX_TRACKS)continue;
        int rend=t.kind==GM_TRACK_VIDEO && t.src_index==gm_stream_selected_video(S.gm)?R_VCOPY:
                 t.kind==GM_TRACK_AUDIO && S.routes[t.src_index]==KR_AUDIO_COPY?R_AUDIO+t.src_index:-1;
        if(rend>=0 && gm_stream_track_init(S.gm,t.src_index,&init,e,sizeof e)==0)
            cache_put(rend,-1,init.data,init.len,0);
        free(init.data);
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
    if(source_interrupted((void *)(uintptr_t)ticket)) {
        result=KR_FAILED;
        set_message(ticket!=atomic_load(&request_ticket) ? "AirPlay canceled." : "The video took too long to open for AirPlay. Try again.");
    }
    atomic_store(&S.startup_deadline_ms,0);
    if(result==KR_READY || result==KR_NOT_NEEDED)phase_for(ticket,"ready");
    else if(ticket==atomic_load(&request_ticket))phase_for(ticket,"failed");
    if(result!=KR_READY) { pthread_mutex_lock(&N.lock);if(N.ticket==ticket)N.expected=0;pthread_mutex_unlock(&N.lock); }
    if (result != KR_READY) { log_line("start result %d: %s", result, S.message); teardown_locked(); }
    atomic_store(&S.state, result);
    pthread_mutex_unlock(&S.lock);
    return result;
}

int kr_remux_start(const char *url,int lan,int compat,char *out,int outlen) {
    return kr_remux_start_for(kr_remux_begin(lan),url,lan,compat,out,outlen);
}

int kr_remux_prime_for(unsigned ticket,double seconds) {
    pthread_mutex_lock(&S.lock);
    int r=KR_FAILED;
    if(ticket!=atomic_load(&S.ticket) || ticket!=atomic_load(&request_ticket) || atomic_load(&S.state)!=KR_READY)goto done;
    if(S.prepared){r=KR_READY;goto done;}
    double began=now_ms();phase_for(ticket,"opening");
    atomic_store(&S.startup_deadline_ms,(long long)(began+55000));
    int seg=gm_stream_time_to_segment(S.gm,isfinite(seconds) && seconds>0?seconds:0);
    gm_buf part={0};char err[256]="";
    int video=S.compat?R_VCOMPAT:R_VCOPY;
    int made=get_part(video,seg,&part,err,sizeof err);free(part.data);part=(gm_buf){0};
    int audio=gm_stream_selected_audio(S.gm);
    if(audio<0 || audio>=MAX_TRACKS || !S.routes[audio]) {
        audio=-1;for(int i=0;i<MAX_TRACKS;i++)if(S.routes[i]){audio=i;break;}
    }
    if(made==0 && audio>=0)made=get_part(R_AUDIO+audio,seg,&part,err,sizeof err);
    free(part.data);
    atomic_store(&S.startup_deadline_ms,0);
    if(made==0 && !source_interrupted((void *)(uintptr_t)ticket)) {
        // Priming is not consumption: keep these units fresh until the receiver takes them. Otherwise
        // high-bitrate speculative segments could evict the first unit before Roku finishes launching.
        pthread_mutex_lock(&C.lock);
        for(int i=0;i<C.n;i++)if(C.e[i].seg==seg && (C.e[i].rend==video || C.e[i].rend==R_AUDIO+audio))C.e[i].fresh=1;
        pthread_mutex_unlock(&C.lock);
        prefetch_after(video,seg);if(audio>=0)prefetch_after(R_AUDIO+audio,seg);
        r=KR_READY;phase_for(ticket,"ready");
        log_line("startup: buffered video and audio at %.1f s (segment %d) in %.0f ms",seconds,seg,now_ms()-began);
    } else if(ticket==atomic_load(&request_ticket)) {
        set_message("The movie could not be buffered from Drive in time. Try again.");phase_for(ticket,"failed");
        log_line("startup: buffering failed after %.0f ms: %s",now_ms()-began,err);
    }
done:
    pthread_mutex_unlock(&S.lock);return r;
}
void kr_remux_set_prefetch(int on) { atomic_store(&pf_on, on != 0); }
